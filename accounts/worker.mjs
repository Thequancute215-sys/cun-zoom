/** Account portal and one-time licenses. No Zoom/AI credentials or lesson data here. */
const encoder = new TextEncoder();
const SESSION_SECONDS = 7 * 86400;
const now = () => Math.floor(Date.now() / 1000);
const random = (bytes = 32) => Array.from(crypto.getRandomValues(new Uint8Array(bytes)), n => n.toString(16).padStart(2, '0')).join('');
const hash = async value => Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', encoder.encode(value))), n => n.toString(16).padStart(2, '0')).join('');
class Problem extends Error { constructor(message, status = 400) { super(message); this.status = status; } }
const fail = (message, status) => { throw new Problem(message, status); };
function identity(value) {
  if (typeof value !== 'string' || value.length > 254) fail('Nhập email hoặc số điện thoại hợp lệ.');
  const text = value.trim().toLowerCase();
  if (/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(text)) return text;
  if (/^\+[1-9][0-9]{7,14}$/.test(text)) return text;
  fail('Nhập email hoặc số điện thoại quốc tế, ví dụ +84901234567.');
}
async function mac(secret, value) {
  const key = await crypto.subtle.importKey('raw', encoder.encode(secret), {name: 'HMAC', hash: 'SHA-256'}, false, ['sign']);
  return Array.from(new Uint8Array(await crypto.subtle.sign('HMAC', key, encoder.encode(value))), n => n.toString(16).padStart(2, '0')).join('');
}
function constantEqual(a, b) {
  const aa = encoder.encode(a), bb = encoder.encode(b);
  let diff = aa.length ^ bb.length;
  for (let i = 0; i < Math.max(aa.length, bb.length); i++) diff |= (aa[i] || 0) ^ (bb[i] || 0);
  return diff === 0;
}
function settings(env) {
  if (!env.OTP_SECRET || env.OTP_SECRET.length < 32 || !env.ADMIN_TOKEN || env.ADMIN_TOKEN.length < 32) fail('Dịch vụ tài khoản chưa được cấu hình.', 503);
  const origin = new URL(env.PUBLIC_ORIGIN);
  if (origin.origin !== env.PUBLIC_ORIGIN || (origin.protocol !== 'https:' && !['localhost', '127.0.0.1'].includes(origin.hostname))) fail('Cần cấu hình địa chỉ HTTPS của dịch vụ.', 503);
  return origin;
}
function headers() {
  return {'Cache-Control': 'no-store', 'Content-Type': 'application/json; charset=utf-8',
    'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer',
    'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"};
}
function json(value, status = 200, extra = {}) { return new Response(JSON.stringify(value), {status, headers: {...headers(), ...extra}}); }
async function body(request) {
  if (!(request.headers.get('Content-Type') || '').startsWith('application/json')) fail('Cần nội dung JSON.', 415);
  const reader = request.body?.getReader();
  if (!reader) fail('Thiếu nội dung yêu cầu.');
  let length = 0; const chunks = [];
  while (true) {
    const {done, value} = await reader.read(); if (done) break;
    length += value.byteLength;
    if (length > 8192) { await reader.cancel(); fail('Yêu cầu quá lớn.', 413); }
    chunks.push(value);
  }
  const bytes = new Uint8Array(length); let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.length; }
  try { const parsed = JSON.parse(new TextDecoder().decode(bytes)); if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) return parsed; } catch {}
  fail('JSON không hợp lệ.');
}
async function limit(env, label, subject, max, seconds) {
  const time = now(), start = Math.floor(time / seconds) * seconds;
  const bucket = `${label}:${await mac(env.OTP_SECRET, subject)}:${start}`;
  const row = await env.DB.prepare('INSERT INTO limits(bucket,hits,expires) VALUES (?,1,?) ON CONFLICT(bucket) DO UPDATE SET hits=hits+1 RETURNING hits').bind(bucket, start + seconds).first();
  if (row.hits > max) fail('Bạn thao tác quá nhanh. Vui lòng thử lại sau.', 429);
}
async function sendOTP(env, recipient, code) {
  let url, init;
  if (recipient.startsWith('+')) {
    if (env.SMS_ENABLED !== 'true' || !env.TWILIO_ACCOUNT_SID || !env.TWILIO_AUTH_TOKEN || !env.TWILIO_FROM) fail('OTP qua số điện thoại chưa được bật. Hãy dùng email.', 503);
    if (!/^AC[a-fA-F0-9]{32}$/.test(env.TWILIO_ACCOUNT_SID)) fail('Dịch vụ SMS chưa được cấu hình.', 503);
    url = `https://api.twilio.com/2010-04-01/Accounts/${env.TWILIO_ACCOUNT_SID}/Messages.json`;
    init = {method: 'POST', headers: {'Authorization': 'Basic ' + btoa(`${env.TWILIO_ACCOUNT_SID}:${env.TWILIO_AUTH_TOKEN}`)}, body: new URLSearchParams({To: recipient, From: env.TWILIO_FROM, Body: `Cún Zoom: mã xác minh ${code}, hết hạn sau 5 phút. Không chia sẻ mã này.`})};
  } else {
    if (!env.RESEND_API_KEY || !env.EMAIL_FROM) fail('Dịch vụ gửi email chưa được cấu hình.', 503);
    url = 'https://api.resend.com/emails';
    init = {method: 'POST', headers: {'Authorization': 'Bearer ' + env.RESEND_API_KEY, 'Content-Type': 'application/json'}, body: JSON.stringify({from: env.EMAIL_FROM, to: [recipient], subject: 'Mã xác minh Cún Zoom', text: `Mã xác minh của bạn: ${code}\nMã hết hạn sau 5 phút và chỉ dùng một lần. Nếu không yêu cầu mã, hãy bỏ qua email này.`})};
  }
  try { const result = await fetch(url, {...init, redirect: 'manual', signal: AbortSignal.timeout(10000)}); if (result.ok) { await result.body?.cancel(); return; } await result.body?.cancel(); } catch {}
  fail('Chưa gửi được OTP. Vui lòng thử lại sau.', 503);
}
async function authenticate(request, env) {
  const bearer = request.headers.get('Authorization');
  const cookie = (request.headers.get('Cookie') || '').split(';').map(s => s.trim()).find(s => s.startsWith('cz_session='));
  const token = bearer?.startsWith('Bearer ') ? bearer.slice(7) : cookie?.slice(11);
  if (!token || !/^[a-f0-9]{64}$/.test(token)) fail('Vui lòng đăng nhập.', 401);
  const digest = await hash(token);
  const row = await env.DB.prepare('SELECT users.id,users.identity FROM sessions JOIN users ON users.id=sessions.user_id WHERE sessions.digest=? AND sessions.expires>?').bind(digest, now()).first();
  if (!row) fail('Phiên đã hết hạn. Vui lòng đăng nhập lại.', 401);
  return {...row, session: digest};
}
const cookie = (token, origin, age = SESSION_SECONDS) => `cz_session=${token}; Path=/; HttpOnly; SameSite=Strict; Max-Age=${age}${origin.protocol === 'https:' ? '; Secure' : ''}`;
function device(data) {
  if (typeof data.device_id !== 'string' || !/^[a-f0-9-]{32,64}$/.test(data.device_id)) fail('Thiết bị không hợp lệ.');
  return data.device_id;
}
async function licenseFor(env, user, id, active = true) {
  const row = await env.DB.prepare('SELECT * FROM licenses WHERE id=? AND owner_id=? AND revoked=0').bind(String(id || ''), user.id).first();
  if (!row || (active && (!row.expires || row.expires <= now()))) fail('Bản quyền không còn hiệu lực.', 403);
  return row;
}
async function api(request, env, url, origin) {
  const path = url.pathname;
  if (request.method !== 'POST') fail('Phương thức không được hỗ trợ.', 405);
  if (request.headers.get('Origin') && request.headers.get('Origin') !== origin.origin) fail('Nguồn yêu cầu không hợp lệ.', 403);
  const data = await body(request);
  const ip = request.headers.get('CF-Connecting-IP') || 'local';
  await limit(env, 'requests', ip, 180, 60);
  if (path.startsWith('/api/admin/')) {
    const supplied = request.headers.get('Authorization') || '';
    if (!constantEqual(supplied, 'Bearer ' + env.ADMIN_TOKEN)) fail('Không có quyền quản trị.', 403);
    if (path === '/api/admin/grant') {
      const recipient = identity(data.identity), days = data.days, devices = data.device_limit;
      if (!Number.isInteger(days) || days < 1 || days > 3650 || !Number.isInteger(devices) || devices < 1 || devices > 10) fail('Thời hạn hoặc số thiết bị không hợp lệ.');
      const id = crypto.randomUUID();
      await env.DB.batch([
        env.DB.prepare('INSERT INTO licenses(id,identity,days,device_limit,created) VALUES (?,?,?,?,?)').bind(id, recipient, days, devices, now()),
        env.DB.prepare('INSERT INTO audit(action,license_id,created) VALUES (?,?,?)').bind('grant', id, now())
      ]);
      return json({id, identity: recipient, days, device_limit: devices});
    }
    if (path === '/api/admin/revoke') {
      const results = await env.DB.batch([
        env.DB.prepare('UPDATE licenses SET revoked=1 WHERE id=? RETURNING id').bind(String(data.license_id || '')),
        env.DB.prepare('INSERT INTO audit(action,license_id,created) SELECT ?,id,? FROM licenses WHERE id=?').bind('revoke', now(), String(data.license_id || ''))
      ]);
      if (!results[0].results.length) fail('Không tìm thấy bản quyền.', 404);
      return json({ok: true});
    }
    fail('Không tìm thấy.', 404);
  }
  if (path === '/api/otp/request') {
    const recipient = identity(data.identity);
    await limit(env, 'otp-minute', recipient, 1, 60);
    await limit(env, 'otp-hour', recipient, 5, 3600);
    await limit(env, 'otp-ip', ip, 15, 3600);
    const daily = Number(env.OTP_DAILY_LIMIT || 100);
    if (!Number.isInteger(daily) || daily < 1 || daily > 10000) fail('Hạn mức OTP chưa hợp lệ.', 503);
    await limit(env, 'otp-budget', 'global', daily, 86400);
    // Rejection sampling avoids modulo bias in the six digit code.
    let number; do { number = crypto.getRandomValues(new Uint32Array(1))[0]; } while (number >= 4294000000);
    const code = String(number % 1000000).padStart(6, '0'), id = random();
    await env.DB.batch([
      env.DB.prepare('UPDATE otp SET used=1 WHERE identity=?').bind(recipient),
      env.DB.prepare('INSERT INTO otp(id,identity,digest,expires,created) VALUES (?,?,?,?,?)').bind(id, recipient, await mac(env.OTP_SECRET, id + ':' + code), now() + 300, now()),
      env.DB.prepare('DELETE FROM otp WHERE expires<?').bind(now() - 86400),
      env.DB.prepare('DELETE FROM limits WHERE expires<?').bind(now() - 86400),
      env.DB.prepare('DELETE FROM sessions WHERE expires<?').bind(now())
    ]);
    try { await sendOTP(env, recipient, code); }
    catch (error) { await env.DB.prepare('UPDATE otp SET used=1 WHERE id=?').bind(id).run(); throw error; }
    return json({challenge: id, expires_in: 300, message: 'OTP đã được gửi. Kiểm tra cả thư rác.'});
  }
  if (path === '/api/otp/verify') {
    await limit(env, 'verify-ip', ip, 30, 600);
    if (typeof data.challenge !== 'string' || !/^[a-f0-9]{64}$/.test(data.challenge) || typeof data.code !== 'string' || !/^[0-9]{6}$/.test(data.code)) fail('OTP không hợp lệ hoặc đã hết hạn.');
    // Increment before testing the digest; consume with an atomic conditional update.
    const row = await env.DB.prepare('UPDATE otp SET attempts=attempts+1 WHERE id=? AND used=0 AND expires>? AND attempts<5 RETURNING *').bind(data.challenge, now()).first();
    if (!row || !constantEqual(row.digest, await mac(env.OTP_SECRET, row.id + ':' + data.code))) fail('OTP không hợp lệ hoặc đã hết hạn.');
    const claimed = await env.DB.prepare('UPDATE otp SET used=1 WHERE id=? AND used=0 RETURNING identity').bind(row.id).first();
    if (!claimed) fail('OTP không hợp lệ hoặc đã hết hạn.');
    await env.DB.prepare('INSERT INTO users(id,identity,created) VALUES (?,?,?) ON CONFLICT(identity) DO NOTHING').bind(crypto.randomUUID(), row.identity, now()).run();
    const user = await env.DB.prepare('SELECT id,identity FROM users WHERE identity=?').bind(row.identity).first();
    const token = random();
    await env.DB.prepare('INSERT INTO sessions(digest,user_id,expires) VALUES (?,?,?)').bind(await hash(token), user.id, now() + SESSION_SECONDS).run();
    return json({identity: user.identity, ...(data.client === 'desktop' ? {token} : {})}, 200, {'Set-Cookie': cookie(token, origin)});
  }
  const user = await authenticate(request, env);
  if (path === '/api/logout') {
    await env.DB.prepare('DELETE FROM sessions WHERE digest=?').bind(user.session).run();
    return json({ok: true}, 200, {'Set-Cookie': cookie('', origin, 0)});
  }
  if (path === '/api/me') {
    const rows = await env.DB.prepare('SELECT id,days,device_limit,expires,revoked,owner_id,key_digest FROM licenses WHERE identity=? ORDER BY created DESC,id').bind(user.identity).all();
    const licenses = [];
    for (const row of rows.results) {
      const devices = await env.DB.prepare('SELECT id,name,created,last_seen FROM devices WHERE license_id=?').bind(row.id).all();
      licenses.push({id: row.id, days: row.days, device_limit: row.device_limit, expires: row.expires, status: row.revoked ? 'revoked' : row.owner_id ? (row.expires > now() ? 'active' : 'expired') : row.key_digest ? 'issued' : 'pending', devices: devices.results});
    }
    return json({identity: user.identity, licenses, download_url: /^https:\/\//.test(env.DOWNLOAD_URL || '') ? env.DOWNLOAD_URL : null});
  }
  if (path === '/api/licenses/key') {
    const raw = 'CZ-' + random(20).toUpperCase();
    const row = await env.DB.prepare('UPDATE licenses SET key_digest=? WHERE id=? AND identity=? AND key_digest IS NULL AND owner_id IS NULL AND revoked=0 RETURNING id').bind(await hash(raw), String(data.license_id || ''), user.identity).first();
    if (!row) fail('Mã đã được cấp hoặc bạn chưa được cấp quyền mua.', 409);
    // The raw key exists only in this response; never store it or log it.
    return json({key: raw, license_id: row.id});
  }
  if (path === '/api/licenses/redeem') {
    await limit(env, 'redeem', user.id, 10, 600);
    const key = String(data.key || '').trim().toUpperCase();
    if (!/^CZ-[A-F0-9]{40}$/.test(key)) fail('Mã bản quyền không hợp lệ.');
    const row = await env.DB.prepare('UPDATE licenses SET owner_id=?,expires=?+days*86400 WHERE key_digest=? AND identity=? AND owner_id IS NULL AND revoked=0 RETURNING id,expires,device_limit').bind(user.id, now(), await hash(key), user.identity).first();
    if (!row) fail('Mã không hợp lệ, đã dùng hoặc không thuộc tài khoản này.', 409);
    return json(row);
  }
  if (path === '/api/devices/activate') {
    const id = device(data), license = await licenseFor(env, user, data.license_id);
    const name = typeof data.name === 'string' ? data.name.trim().slice(0, 80) : '';
    if (!name) fail('Nhập tên thiết bị.');
    try {
      await env.DB.prepare('INSERT INTO devices(id,license_id,name,created,last_seen) SELECT ?,id,?,?,? FROM licenses WHERE id=? AND owner_id=? AND revoked=0 AND expires>? ON CONFLICT(license_id,id) DO UPDATE SET name=excluded.name,last_seen=excluded.last_seen').bind(id, name, now(), now(), license.id, user.id, now()).run();
    } catch (error) { if (String(error).includes('device_limit')) fail('Đã đủ số thiết bị. Gỡ một thiết bị trong tài khoản trước.', 409); throw error; }
    return json({ok: true, license_id: license.id});
  }
  if (path === '/api/devices/remove') {
    const id = device(data);
    await env.DB.prepare('DELETE FROM devices WHERE id=? AND license_id IN (SELECT id FROM licenses WHERE id=? AND owner_id=?)').bind(id, String(data.license_id || ''), user.id).run();
    return json({ok: true});
  }
  if (path === '/api/licenses/check') {
    const id = device(data), license = await licenseFor(env, user, data.license_id);
    const row = await env.DB.prepare('UPDATE devices SET last_seen=? WHERE id=? AND license_id=? RETURNING id').bind(now(), id, license.id).first();
    if (!row) fail('Thiết bị chưa kích hoạt hoặc đã bị gỡ.', 403);
    return json({active: true, license_id: license.id, expires: license.expires, recheck_after: 60});
  }
  fail('Không tìm thấy.', 404);
}
export default {
  async fetch(request, env) {
    try {
      const url = new URL(request.url), origin = settings(env);
      if (url.host !== origin.host) fail('Host không hợp lệ.', 403);
      if (url.pathname === '/health' && request.method === 'GET') return json({product: 'CunZoom Accounts'});
      if (url.pathname.startsWith('/api/')) return await api(request, env, url, origin);
      if (request.method !== 'GET') fail('Phương thức không được hỗ trợ.', 405);
      const known = {'/': '/account.html', '/account.js': '/account.js', '/account.css': '/account.css', '/logo.svg': '/logo.svg'};
      if (!known[url.pathname]) fail('Không tìm thấy.', 404);
      const asset = await env.ASSETS.fetch(new Request(new URL(known[url.pathname], request.url)));
      if (!asset.ok) return json({error: 'Thiếu giao diện tài khoản.'}, 503);
      const content = (await asset.text()).replaceAll('__TOKEN__', '').replaceAll('__MODE__', 'portal');
      return new Response(content, {headers: {...headers(), 'Content-Type': asset.headers.get('Content-Type') || 'text/plain'}});
    } catch (error) {
      return json({error: error instanceof Problem ? error.message : 'Dịch vụ tạm thời chưa xử lý được yêu cầu.'}, error instanceof Problem ? error.status : 503);
    }
  }
};
