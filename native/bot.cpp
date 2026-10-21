#define NOMINMAX
#include <cstdint>
#include <windows.h>
#include <wincrypt.h>
#include <gdiplus.h>
#include <zoom_sdk.h>
#include <auth_service_interface.h>
#include <meeting_service_interface.h>
#include <meeting_service_components/meeting_recording_interface.h>
#include <meeting_service_components/meeting_audio_interface.h>
#include <meeting_service_components/meeting_participants_ctrl_interface.h>
#include <meeting_service_components/meeting_sharing_interface.h>
#include <rawdata/rawdata_audio_helper_interface.h>
#include <rawdata/rawdata_renderer_interface.h>
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
#include "adapters.h"
using namespace ZOOM_SDK_NAMESPACE;
static std::mutex outputMutex,audioMutex;
static IAuthService* auth=nullptr;
static IMeetingService* meeting=nullptr;
static IZoomSDKAudioRawDataHelper* audioHelper=nullptr;
static IZoomSDKRenderer* renderer=nullptr;
static std::atomic<bool> rawStarted(false),quitting(false),authSeen(false),inMeeting(false);
static bool permissionRequested=false,authOnly=true;
static int exitCode=0;
static DWORD mainThread=0;
static std::wstring jwt,number,passcode,displayName,obf,outputDir;
static uint64_t audioBytes=0,lastAudioNotice=0,lastSlide=0;
static unsigned slideCount=0;
static uint32_t sampleRate=0,channels=0;
static std::fstream wave;
static void event(const char* state,int code=0,uint64_t amount=0){std::lock_guard<std::mutex> l(outputMutex);std::cout<<"{\"state\":\""<<state<<"\",\"code\":"<<code<<",\"amount\":"<<amount<<"}"<<std::endl;}
static std::string decode(const std::string& s){if(s.empty())return {};DWORD len=0;if(!CryptStringToBinaryA(s.c_str(),(DWORD)s.size(),CRYPT_STRING_BASE64,nullptr,&len,nullptr,nullptr))throw 1;std::string r(len,'\0');if(!CryptStringToBinaryA(s.c_str(),(DWORD)s.size(),CRYPT_STRING_BASE64,(BYTE*)&r[0],&len,nullptr,nullptr))throw 1;return r;}
static std::wstring wide(const std::string& s){if(s.empty())return {};int n=MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,s.data(),(int)s.size(),nullptr,0);if(!n)throw 1;std::wstring r(n,L'\0');MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,s.data(),(int)s.size(),&r[0],n);return r;}
static std::wstring field(){std::string s;if(!std::getline(std::cin,s)||s.size()>65536)throw 1;return wide(decode(s));}
static void waveHeader(){if(!wave.is_open())return;wave.seekp(0);uint32_t riff=(uint32_t)audioBytes+36,fmt=16,rate=sampleRate*channels*2,data=(uint32_t)audioBytes;uint16_t pcm=1,ch=(uint16_t)channels,block=ch*2,bits=16;wave.write("RIFF",4);wave.write((char*)&riff,4);wave.write("WAVEfmt ",8);wave.write((char*)&fmt,4);wave.write((char*)&pcm,2);wave.write((char*)&ch,2);wave.write((char*)&sampleRate,4);wave.write((char*)&rate,4);wave.write((char*)&block,2);wave.write((char*)&bits,2);wave.write("data",4);wave.write((char*)&data,4);wave.flush();wave.seekp(0,std::ios::end);}
class Audio : public IZoomSDKAudioRawDataDelegate { public:
 void onMixedAudioRawDataReceived(AudioRawData* d) override {
  if(!rawStarted||!d||!d->GetBuffer()||!d->GetBufferLen())return;
  std::lock_guard<std::mutex> l(audioMutex);
  if(!wave.is_open()){sampleRate=d->GetSampleRate();channels=d->GetChannelNum();if(!sampleRate||channels<1||channels>2){event("audio_format_error");return;}wave.open((outputDir+L"\\01_Tai_lieu_goc\\am_thanh.wav").c_str(),std::ios::binary|std::ios::out|std::ios::in|std::ios::trunc);if(!wave){event("audio_write_error");quitting=true;return;}waveHeader();}
  if(sampleRate!=d->GetSampleRate()||channels!=d->GetChannelNum()){event("audio_format_changed");quitting=true;return;}
  wave.write(d->GetBuffer(),d->GetBufferLen());audioBytes+=d->GetBufferLen();
  if(!wave){event("audio_write_error");quitting=true;return;}
  if(GetTickCount64()-lastAudioNotice>5000){waveHeader();lastAudioNotice=GetTickCount64();event("receiving_audio",0,audioBytes);}
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
 void onShareCursorDataReceived(ZoomSDKShareCursorData) override {}
 void onRawDataFrameReceived(YUVRawDataI420* d) override {
  auto now=GetTickCount64();if(!rawStarted||!d||(lastSlide&&now-lastSlide<30000))return;
  unsigned sw=d->GetStreamWidth(),sh=d->GetStreamHeight();if(!sw||!sh||sw>8192||sh>8192||!d->GetYBuffer()||!d->GetUBuffer()||!d->GetVBuffer())return;
  if(d->GetBufferLen()<(uint64_t)sw*sh*3/2)return;lastSlide=now;
  unsigned width=(std::min)(sw,1600u),height=(unsigned)((uint64_t)width*sh/sw);if(!height)return;
  Gdiplus::Bitmap bitmap(width,height,PixelFormat24bppRGB);Gdiplus::Rect rect(0,0,width,height);Gdiplus::BitmapData bits;
  if(bitmap.LockBits(&rect,Gdiplus::ImageLockModeWrite,PixelFormat24bppRGB,&bits)!=Gdiplus::Ok)return;
  auto y=(unsigned char*)d->GetYBuffer(),u=(unsigned char*)d->GetUBuffer(),v=(unsigned char*)d->GetVBuffer();
  for(unsigned row=0;row<height;row++){unsigned sy=(uint64_t)row*sh/height;auto dst=(unsigned char*)bits.Scan0+row*bits.Stride;for(unsigned col=0;col<width;col++){unsigned sx=(uint64_t)col*sw/width;int Y=y[sy*sw+sx]-16,U=u[(sy/2)*((sw+1)/2)+sx/2]-128,V=v[(sy/2)*((sw+1)/2)+sx/2]-128;dst[col*3]=clamp((298*Y+516*U+128)>>8);dst[col*3+1]=clamp((298*Y-100*U-208*V+128)>>8);dst[col*3+2]=clamp((298*Y+409*V+128)>>8);}}
  bitmap.UnlockBits(&bits);unsigned rotation=d->GetRotation();if(rotation==90)bitmap.RotateFlip(Gdiplus::Rotate90FlipNone);else if(rotation==180)bitmap.RotateFlip(Gdiplus::Rotate180FlipNone);else if(rotation==270)bitmap.RotateFlip(Gdiplus::Rotate270FlipNone);
  CLSID jpeg={0x557cf401,0x1a04,0x11d3,{0x9a,0x73,0x00,0x00,0xf8,0x1e,0xf3,0x2e}};
  wchar_t name[64];swprintf_s(name,L"\\01_Tai_lieu_goc\\slide_%04u.jpg",++slideCount);
  if(bitmap.Save((outputDir+name).c_str(),&jpeg)==Gdiplus::Ok)event("slide_saved",0,slideCount);else event("slide_write_error");
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
 void onAuthenticationReturn(AuthResult result) override {authSeen=true;event("sdk_authenticated",(int)result);if(result!=AUTHRET_SUCCESS){exitCode=20;quitting=true;return;}if(authOnly){quitting=true;return;}if(!prepareMeeting()){exitCode=8;quitting=true;return;}audioHelper=getAudio?getAudio():nullptr;if(!audioHelper){event("audio_helper_missing");exitCode=9;quitting=true;return;}auto mic=audioHelper->setExternalAudioSource(&silentMic);if(mic!=SDKERR_SUCCESS){event("silent_microphone_setup_failed",mic);exitCode=9;quitting=true;return;}JoinParam p;auto& j=p.param.withoutloginuserJoin;j.meetingNumber=_wcstoui64(number.c_str(),nullptr,10);j.userName=displayName.c_str();j.psw=passcode.c_str();j.onBehalfToken=obf.empty()?nullptr:obf.c_str();j.isVideoOff=true;j.isAudioOff=true;j.isMyVoiceInMix=false;j.isAudioRawDataStereo=false;j.eAudioRawdataSamplingRate=AudioRawdataSamplingRate_32K;j.eVideoRawdataColorspace=VideoRawdataColorspace_BT601_L;auto resultJoin=meeting->Join(p);event("join_requested",resultJoin);if(resultJoin!=SDKERR_SUCCESS){exitCode=31;quitting=true;}}
} authEvents;
static bool prepareMeeting(){auto result=createMeetingService(&meeting);event("meeting_service_created",result);if(result!=SDKERR_SUCCESS||!meeting)return false;meeting->SetEvent(&meetingEvents);auto recording=meeting->GetMeetingRecordingController();if(recording)recording->SetEvent(&recordingEvents);return true;}
int wmain(int argc,wchar_t** argv){
 if(argc==3&&wcscmp(argv[2],L"check")==0){SetDllDirectoryW(argv[1]);auto library=LoadLibraryW((std::wstring(argv[1])+L"\\sdk.dll").c_str());if(!library){event("sdk_load_failed",GetLastError());return 5;}auto initialize=(SDKError(*)(InitParam&))GetProcAddress(library,"InitSDK");auto clean=(SDKError(*)())GetProcAddress(library,"CleanUPSDK");if(!initialize||!clean)return 6;Gdiplus::GdiplusStartupInput input;ULONG_PTR token=0;Gdiplus::GdiplusStartup(&token,&input,nullptr);InitParam parameters;parameters.strWebDomain=L"https://zoom.us";parameters.enableLogByDefault=false;parameters.enableGenerateDump=false;auto status=initialize(parameters);event("sdk_loaded",status);if(status==SDKERR_SUCCESS)clean();Gdiplus::GdiplusShutdown(token);return status==SDKERR_SUCCESS?0:7;}
 if(argc!=3){event("invalid_launch");return 2;}mainThread=GetCurrentThreadId();MSG msg;PeekMessage(&msg,nullptr,WM_USER,WM_USER,PM_NOREMOVE);
 try{auto mode=field();authOnly=mode==L"auth-test";jwt=field();number=field();passcode=field();displayName=field();obf=field();outputDir=field();}catch(...){event("invalid_input");return 3;}
 if(jwt.empty()||(!authOnly&&(number.empty()||outputDir.empty()||obf.empty()))){event("missing_authorization");return 4;}
 SetDllDirectoryW(argv[1]);std::wstring dll=std::wstring(argv[1])+L"\\sdk.dll";HMODULE sdk=LoadLibraryW(dll.c_str());if(!sdk){event("sdk_load_failed",GetLastError());return 5;}
 auto init=(SDKError(*)(InitParam&))GetProcAddress(sdk,"InitSDK");auto cleanup=(SDKError(*)())GetProcAddress(sdk,"CleanUPSDK");auto createAuth=(SDKError(*)(IAuthService**))GetProcAddress(sdk,"CreateAuthService");createMeetingService=(SDKError(*)(IMeetingService**))GetProcAddress(sdk,"CreateMeetingService");
 getAudio=(IZoomSDKAudioRawDataHelper*(*)())GetProcAddress(sdk,"GetAudioRawdataHelper");makeRenderer=(SDKError(*)(IZoomSDKRenderer**,IZoomSDKRendererDelegate*))GetProcAddress(sdk,"createRenderer");destroyRenderer=(SDKError(*)(IZoomSDKRenderer*))GetProcAddress(sdk,"destroyRenderer");
 if(!init||!cleanup||!createAuth||!createMeetingService){event("sdk_export_missing");return 6;}
 Gdiplus::GdiplusStartupInput gdipInput;ULONG_PTR gdipToken=0;Gdiplus::GdiplusStartup(&gdipToken,&gdipInput,nullptr);
 InitParam ip;ip.strWebDomain=L"https://zoom.us";ip.enableLogByDefault=false;ip.enableGenerateDump=false;auto result=init(ip);event("sdk_initialized",result);if(result!=SDKERR_SUCCESS)return 7;
 auto authServiceResult=createAuth(&auth);event("auth_service_created",authServiceResult);if(!auth){event("sdk_service_missing");cleanup();return 8;}

 auth->SetEvent(&authEvents);AuthContext ac;ac.jwt_token=jwt.c_str();result=auth->SDKAuth(ac);event("sdk_auth_requested",result);if(result!=SDKERR_SUCCESS){cleanup();return 10;}
 std::thread([](){std::string cmd;while(std::getline(std::cin,cmd)){if(cmd=="STOP")break;}PostThreadMessage(mainThread,WM_APP+1,0,0);}).detach();
 auto began=GetTickCount64(),lastTick=began;bool sawMeeting=false;
 while(!quitting){while(PeekMessage(&msg,nullptr,0,0,PM_REMOVE)){if(msg.message==WM_QUIT||msg.message==WM_APP+1){quitting=true;break;}TranslateMessage(&msg);DispatchMessage(&msg);}auto now=GetTickCount64();if(!authSeen&&now-began>60000){event("sdk_auth_timeout");exitCode=21;quitting=true;}if(!authOnly&&!sawMeeting&&now-began>180000){event("admission_timeout");exitCode=32;quitting=true;}if(inMeeting)sawMeeting=true;if(now-began>10800000){event("session_time_limit");quitting=true;}
  if(rawStarted&&now-lastTick>3000){lastTick=now;auto share=meeting->GetMeetingShareController();auto users=share?share->GetViewableSharingUserList():nullptr;unsigned source=0;if(users)for(int i=0;i<users->GetCount()&&!source;i++){auto list=share->GetSharingSourceInfoList(users->GetItem(i));if(list&&list->GetCount())source=list->GetItem(0).shareSourceID;}if(source&&makeRenderer){if(!renderer)makeRenderer(&renderer,&slideDelegate);if(renderer&&renderer->getSubscribeId()!=source){renderer->unSubscribe();auto s=renderer->subscribe(source,RAW_DATA_TYPE_SHARE);event("share_subscribe",s);}}}
  MsgWaitForMultipleObjects(0,nullptr,FALSE,250,QS_ALLINPUT);
 }
 stopRaw();if(meeting&&!authOnly)meeting->Leave(LEAVE_MEETING);if(renderer&&destroyRenderer)destroyRenderer(renderer);{std::lock_guard<std::mutex> l(audioMutex);waveHeader();if(wave.is_open())wave.close();}event("stopped",exitCode,audioBytes);cleanup();Gdiplus::GdiplusShutdown(gdipToken);return exitCode;
}
