#include <cstdint>
#include <glib.h>
#include <cstdio>
#include <jpeglib.h>
#include <chrono>
#include <csignal>
#include <cstdio>
#include <stdexcept>
#include <zoom_sdk.h>
#include <auth_service_interface.h>
#include <meeting_service_interface.h>
#include <meeting_service_components/meeting_recording_interface.h>
#include <meeting_service_components/meeting_audio_interface.h>
#include <meeting_service_components/meeting_participants_ctrl_interface.h>
#include <meeting_service_components/meeting_sharing_interface.h>
#include <rawdata/rawdata_audio_helper_interface.h>
#include <rawdata/rawdata_renderer_interface.h>
#include <rawdata/zoom_rawdata_api.h>
#include <zoom_sdk_raw_data_def.h>
#include <algorithm>
#include <atomic>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <mutex>
#include <string>
#include <thread>
#include <vector>
#include "linux_adapters.h"
using namespace ZOOM_SDK_NAMESPACE;
static std::mutex outputMutex,audioMutex;
static IAuthService* auth=nullptr;
static IMeetingService* meeting=nullptr;
static IZoomSDKAudioRawDataHelper* audioHelper=nullptr;
static IZoomSDKRenderer* renderer=nullptr;
static std::atomic<bool> rawStarted(false),quitting(false),authSeen(false),inMeeting(false);
static bool permissionRequested=false,authOnly=true;
static int exitCode=0;
static uint64_t ticks(){return std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now().time_since_epoch()).count();}
static std::string jwt,number,passcode,displayName,obf,outputDir;
static uint64_t audioBytes=0,lastAudioNotice=0,lastSlide=0;
static unsigned slideCount=0;
static uint32_t sampleRate=0,channels=0;
static std::fstream wave;
static void event(const char* state,int code=0,uint64_t amount=0){std::lock_guard<std::mutex> l(outputMutex);std::cout<<"{\"state\":\""<<state<<"\",\"code\":"<<code<<",\"amount\":"<<amount<<"}"<<std::endl;}
static std::string decode(const std::string& text){
 static const std::string chars="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
 std::string out;unsigned value=0;int bits=-8;
 for(unsigned char ch:text){if(ch=='=')break;auto pos=chars.find(ch);if(pos==std::string::npos)throw std::runtime_error("base64");value=(value<<6)|pos;bits+=6;if(bits>=0){out.push_back(char((value>>bits)&255));bits-=8;}}
 return out;
}
static std::string field(){std::string text;if(!std::getline(std::cin,text)||text.size()>65536)throw std::runtime_error("input");if(!text.empty()&&text.back()=='\r')text.pop_back();return decode(text);}
static void waveHeader(){if(!wave.is_open())return;wave.seekp(0);uint32_t riff=(uint32_t)audioBytes+36,fmt=16,rate=sampleRate*channels*2,data=(uint32_t)audioBytes;uint16_t pcm=1,ch=(uint16_t)channels,block=ch*2,bits=16;wave.write("RIFF",4);wave.write((char*)&riff,4);wave.write("WAVEfmt ",8);wave.write((char*)&fmt,4);wave.write((char*)&pcm,2);wave.write((char*)&ch,2);wave.write((char*)&sampleRate,4);wave.write((char*)&rate,4);wave.write((char*)&block,2);wave.write((char*)&bits,2);wave.write("data",4);wave.write((char*)&data,4);wave.flush();wave.seekp(0,std::ios::end);}
class Audio : public IZoomSDKAudioRawDataDelegate { public:
 void onMixedAudioRawDataReceived(AudioRawData* d) override {
  if(!rawStarted||!d||!d->GetBuffer()||!d->GetBufferLen())return;
  std::lock_guard<std::mutex> l(audioMutex);
  if(!wave.is_open()){sampleRate=d->GetSampleRate();channels=d->GetChannelNum();if(!sampleRate||channels<1||channels>2){event("audio_format_error");return;}wave.open((outputDir+"/01_Tai_lieu_goc/am_thanh.wav").c_str(),std::ios::binary|std::ios::out|std::ios::in|std::ios::trunc);if(!wave){event("audio_write_error");quitting=true;return;}waveHeader();}
  if(sampleRate!=d->GetSampleRate()||channels!=d->GetChannelNum()){event("audio_format_changed");quitting=true;return;}
  wave.write(d->GetBuffer(),d->GetBufferLen());audioBytes+=d->GetBufferLen();
  if(!wave){event("audio_write_error");quitting=true;return;}
  if(ticks()-lastAudioNotice>5000){waveHeader();lastAudioNotice=ticks();event("receiving_audio",0,audioBytes);}
 }
 void onOneWayAudioRawDataReceived(AudioRawData*,uint32_t) override {}
 void onShareAudioRawDataReceived(AudioRawData*,uint32_t) override {}
 void onOneWayInterpreterAudioRawDataReceived(AudioRawData*,const zchar_t*) override {}
} audioDelegate;
// External microphone intentionally never emits audio; the bot cannot relay the user's microphone.
class SilentMic : public IZoomSDKVirtualAudioMicEvent {public:void onMicInitialize(IZoomSDKAudioRawDataSender*) override{} void onMicStartSend() override{} void onMicStopSend() override{} void onMicUninitialized() override{}} silentMic;
static int clamp(int n){return (std::max)(0,(std::min)(255,n));}
class Slides : public IZoomSDKRendererDelegate {public:
 void onRendererBeDestroyed() override {renderer=nullptr;}
 void onRawDataStatusChanged(RawDataStatus) override {}
 void onRawDataFrameReceived(YUVRawDataI420* d) override {
  auto now=ticks();if(!rawStarted||!d||(lastSlide&&now-lastSlide<30000))return;
  unsigned sw=d->GetStreamWidth(),sh=d->GetStreamHeight();if(!sw||!sh||sw>8192||sh>8192||!d->GetYBuffer()||!d->GetUBuffer()||!d->GetVBuffer())return;
  if(d->GetBufferLen()<(uint64_t)sw*sh*3/2)return;lastSlide=now;
  unsigned width=(std::min)(sw,1600u),height=(unsigned)((uint64_t)width*sh/sw);if(!height)return;
  const unsigned rotation=d->GetRotation();
  const unsigned ow=(rotation==90||rotation==270)?height:width,oh=(rotation==90||rotation==270)?width:height;
  std::vector<unsigned char> rgb((size_t)ow*oh*3);
  auto y=(unsigned char*)d->GetYBuffer(),u=(unsigned char*)d->GetUBuffer(),v=(unsigned char*)d->GetVBuffer();
  for(unsigned row=0;row<height;row++){unsigned sy=(uint64_t)row*sh/height;for(unsigned col=0;col<width;col++){
    unsigned sx=(uint64_t)col*sw/width,dx=col,dy=row;
    if(rotation==90){dx=height-1-row;dy=col;}else if(rotation==180){dx=width-1-col;dy=height-1-row;}else if(rotation==270){dx=row;dy=width-1-col;}
    auto dst=rgb.data()+((size_t)dy*ow+dx)*3;
    int Y=y[sy*sw+sx]-16,U=u[(sy/2)*((sw+1)/2)+sx/2]-128,V=v[(sy/2)*((sw+1)/2)+sx/2]-128;
    dst[0]=clamp((298*Y+409*V+128)>>8);dst[1]=clamp((298*Y-100*U-208*V+128)>>8);dst[2]=clamp((298*Y+516*U+128)>>8);
  }}
  char name[96];snprintf(name,sizeof(name),"/01_Tai_lieu_goc/slide_%04u.jpg",slideCount+1);
  FILE* file=fopen((outputDir+name).c_str(),"wb");if(!file){event("slide_write_error");return;}
  jpeg_compress_struct encoder{};jpeg_error_mgr errors{};encoder.err=jpeg_std_error(&errors);jpeg_create_compress(&encoder);jpeg_stdio_dest(&encoder,file);
  encoder.image_width=ow;encoder.image_height=oh;encoder.input_components=3;encoder.in_color_space=JCS_RGB;
  jpeg_set_defaults(&encoder);jpeg_set_quality(&encoder,85,TRUE);jpeg_start_compress(&encoder,TRUE);
  while(encoder.next_scanline<oh){JSAMPROW line=rgb.data()+(size_t)encoder.next_scanline*ow*3;jpeg_write_scanlines(&encoder,&line,1);}
  jpeg_finish_compress(&encoder);jpeg_destroy_compress(&encoder);int ok=fclose(file);if(!ok)event("slide_saved",0,++slideCount);else event("slide_write_error");
 }
} slideDelegate;
static auto createMeetingService=(SDKError(*)(IMeetingService**))nullptr;
static auto getAudio=(IZoomSDKAudioRawDataHelper*(*)())nullptr;
static auto makeRenderer=(SDKError(*)(IZoomSDKRenderer**,IZoomSDKRendererDelegate*))nullptr;
static auto destroyRenderer=(SDKError(*)(IZoomSDKRenderer*))nullptr;
static void stopRaw(){rawStarted=false;if(audioHelper)audioHelper->unSubscribe();if(renderer)renderer->unSubscribe();if(meeting&&inMeeting)meeting->GetMeetingRecordingController()->StopRawRecording();}
static void tryRaw(){
 if(!meeting||!inMeeting||rawStarted||quitting)return;
 auto r=meeting->GetMeetingRecordingController();if(!r)return;
 auto can=r->CanStartRawRecording();
 if(can==SDKERR_SUCCESS){auto result=r->StartRawRecording();if(result!=SDKERR_SUCCESS){event("raw_start_failed",result);return;}audioHelper=getAudio?getAudio():nullptr;if(!audioHelper){event("audio_helper_missing");quitting=true;return;}rawStarted=true;auto a=audioHelper->subscribe(&audioDelegate);if(a!=SDKERR_SUCCESS){rawStarted=false;r->StopRawRecording();event("audio_subscribe_failed",a);quitting=true;return;}event("host_approved_waiting_audio");}
 else if(!permissionRequested){permissionRequested=true;auto request=r->RequestLocalRecordingPrivilege();event("waiting_record_permission",request);}
}
class RecordingEvents : public IMeetingRecordingCtrlEventAdapter {public:
 void onRecordPrivilegeChanged(bool allowed) override {if(allowed)tryRaw();else if(rawStarted){stopRaw();event("record_permission_revoked");quitting=true;}}
 void onLocalRecordingPrivilegeRequestStatus(RequestLocalRecordingStatus s) override {event("record_permission_response",s);if(s==RequestLocalRecording_Granted)tryRaw();}
} recordingEvents;
class MeetingEvents : public IMeetingServiceEventAdapter {public:
 void onMeetingStatusChanged(MeetingStatus status,int code=0) override {event("meeting_status",(int)status,code);inMeeting=status==MEETING_STATUS_INMEETING;if(inMeeting){auto a=meeting->GetMeetingAudioController();if(a){a->EnablePlayMeetingAudio(false);a->JoinVoip();auto p=meeting->GetMeetingParticipantsController();auto me=p?p->GetMySelfUser():nullptr;if(me)a->MuteAudio(me->GetUserID());}tryRaw();}if(status==MEETING_STATUS_FAILED){exitCode=30;quitting=true;}if(status==MEETING_STATUS_ENDED)quitting=true;}
} meetingEvents;
static bool prepareMeeting();
class AuthEvents : public IAuthServiceEventAdapter {public:
 void onAuthenticationReturn(AuthResult result) override {authSeen=true;event("sdk_authenticated",(int)result);if(result!=AUTHRET_SUCCESS){exitCode=20;quitting=true;return;}if(authOnly){quitting=true;return;}if(!prepareMeeting()){exitCode=8;quitting=true;return;}audioHelper=getAudio?getAudio():nullptr;if(!audioHelper){event("audio_helper_missing");exitCode=9;quitting=true;return;}auto mic=audioHelper->setExternalAudioSource(&silentMic);if(mic!=SDKERR_SUCCESS){event("silent_microphone_setup_failed",mic);exitCode=9;quitting=true;return;}JoinParam p;p.userType=SDK_UT_WITHOUT_LOGIN;auto& j=p.param.withoutloginuserJoin;j.meetingNumber=std::stoull(number);j.userName=displayName.c_str();j.psw=passcode.c_str();j.onBehalfToken=obf.empty()?nullptr:obf.c_str();j.isVideoOff=true;j.isAudioOff=true;j.isMyVoiceInMix=false;j.isAudioRawDataStereo=false;j.eAudioRawdataSamplingRate=AudioRawdataSamplingRate_32K;j.eVideoRawdataColorspace=VideoRawdataColorspace_BT601_L;auto resultJoin=meeting->Join(p);event("join_requested",resultJoin);if(resultJoin!=SDKERR_SUCCESS){exitCode=31;quitting=true;}}
} authEvents;
static bool prepareMeeting(){auto result=createMeetingService(&meeting);event("meeting_service_created",result);if(result!=SDKERR_SUCCESS||!meeting)return false;meeting->SetEvent(&meetingEvents);auto recording=meeting->GetMeetingRecordingController();if(recording)recording->SetEvent(&recordingEvents);return true;}
int main(int argc,char** argv){
 if(argc!=3){event("invalid_launch");return 2;}
 InitParam ip;ip.strWebDomain="https://zoom.us";ip.strSupportUrl="https://zoom.us";ip.enableLogByDefault=false;ip.enableGenerateDump=false;
 if(std::string(argv[2])=="check"){auto result=InitSDK(ip);event("sdk_loaded",result);if(result==SDKERR_SUCCESS)CleanUPSDK();return result==SDKERR_SUCCESS?0:7;}
 if(std::string(argv[2])!="ipc"){event("invalid_launch");return 2;}
 try{auto mode=field();if(mode!="join"&&mode!="auth-test")throw std::runtime_error("mode");authOnly=mode=="auth-test";jwt=field();number=field();passcode=field();displayName=field();obf=field();outputDir=field();}catch(...){event("invalid_input");return 3;}
 if(jwt.empty()||(!authOnly&&(number.empty()||outputDir.empty()||obf.empty()))){event("missing_authorization");return 4;}
 createMeetingService=&CreateMeetingService;getAudio=&GetAudioRawdataHelper;makeRenderer=&createRenderer;destroyRenderer=&ZOOM_SDK_NAMESPACE::destroyRenderer;
 auto result=InitSDK(ip);event("sdk_initialized",result);if(result!=SDKERR_SUCCESS)return 7;
 auto authServiceResult=CreateAuthService(&auth);event("auth_service_created",authServiceResult);if(!auth){event("sdk_service_missing");CleanUPSDK();return 8;}
 auth->SetEvent(&authEvents);AuthContext ac;ac.jwt_token=jwt.c_str();result=auth->SDKAuth(ac);event("sdk_auth_requested",result);if(result!=SDKERR_SUCCESS){CleanUPSDK();return 10;}
 std::signal(SIGTERM,[](int){quitting=true;});std::signal(SIGINT,[](int){quitting=true;});
 std::thread([](){std::string command;while(std::getline(std::cin,command)){if(command=="STOP")break;}quitting=true;}).detach();
 auto began=ticks(),lastTick=began;bool sawMeeting=false;
 while(!quitting){
  while(g_main_context_pending(nullptr))g_main_context_iteration(nullptr,FALSE);
  auto now=ticks();
  if(!authSeen&&now-began>60000){event("sdk_auth_timeout");exitCode=21;quitting=true;}
  if(!authOnly&&!sawMeeting&&now-began>180000){event("admission_timeout");exitCode=32;quitting=true;}
  if(inMeeting)sawMeeting=true;
  if(now-began>10800000){event("session_time_limit");quitting=true;}
  if(rawStarted&&now-lastTick>3000){
   lastTick=now;auto share=meeting->GetMeetingShareController();auto users=share?share->GetViewableSharingUserList():nullptr;unsigned source=0;
   if(users)for(int i=0;i<users->GetCount()&&!source;i++){auto list=share->GetSharingSourceInfoList(users->GetItem(i));if(list&&list->GetCount())source=list->GetItem(0).shareSourceID;}
   if(source&&makeRenderer){if(!renderer)makeRenderer(&renderer,&slideDelegate);if(renderer&&renderer->getSubscribeId()!=source){renderer->unSubscribe();renderer->setRawDataResolution(ZoomSDKResolution_720P);event("share_subscribe",renderer->subscribe(source,RAW_DATA_TYPE_SHARE));}}
  }
  std::this_thread::sleep_for(std::chrono::milliseconds(25));
 }
 stopRaw();if(meeting&&!authOnly)meeting->Leave(LEAVE_MEETING);if(renderer&&destroyRenderer)destroyRenderer(renderer);
 {std::lock_guard<std::mutex> lock(audioMutex);waveHeader();if(wave.is_open())wave.close();}
 event("stopped",exitCode,audioBytes);if(meeting)DestroyMeetingService(meeting);if(auth)DestroyAuthService(auth);CleanUPSDK();return exitCode;
}
