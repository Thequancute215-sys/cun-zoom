import {after, before, test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {Miniflare} from 'miniflare';

let mf, db, serial = 0, rejectDelivery = false;
const messages = [];
const admin = 'synthetic-admin-token-for-tests-only-000000';
async function call(path, data = {}, token, extra = {}) {
  const headers = {'Content-Type': 'application/json', 'CF-Connecting-IP': `198.51.100.${++serial}`, ...extra};
  if (token) headers.Authorization = 'Bearer ' + token;
  const response = await mf.dispatchFetch('http://localhost/api/' + path, {method: 'POST', headers, body: JSON.stringify(data)});
  return {status: response.status, value: await response.json(), headers: response.headers};
}
async function login(identity) {
  const request = await call('otp/request', {identity}); assert.equal(request.status, 200, JSON.stringify(request.value));
  const code = messages.at(-1).code;
  const verified = await call('otp/verify', {challenge: request.value.challenge, code, client: 'desktop'});
  assert.equal(verified.status, 200, JSON.stringify(verified.value));
  return {token: verified.value.token, challenge: request.value.challenge, code};
}
async function grant(identity, devices = 2) {
  const result = await call('admin/grant', {identity, days: 30, device_limit: devices}, admin);
  assert.equal(result.status, 200); return result.value.id;
}
async function active(identity, devices = 2) {
  const {token} = await login(identity), id = await grant(identity, devices);
  const issued = await call('licenses/key', {license_id: id}, token);
  assert.equal(issued.status, 200);
  assert.equal((await call('licenses/redeem', {key: issued.value.key}, token)).status, 200);
  return {token, id, key: issued.value.key};
}
before(async () => {
  mf = new Miniflare({modules: true, scriptPath: fileURLToPath(new URL('../worker.mjs', import.meta.url)),
    compatibilityDate: '2026-08-01', d1Databases: {DB: 'accounts-test'},
    bindings: {PUBLIC_ORIGIN: 'http://localhost', OTP_SECRET: 'synthetic-otp-secret-for-tests-only-000000', ADMIN_TOKEN: admin,
      RESEND_API_KEY: 'synthetic-provider-key', EMAIL_FROM: 'Cún Zoom <test@example.com>', OTP_DAILY_LIMIT: '100',
      SMS_ENABLED: 'false', DOWNLOAD_URL: 'https://example.com/download'},
    serviceBindings: {ASSETS: async request => {
      const name = new URL(request.url).pathname.slice(1);
      const raw = await readFile(new URL('../../web/' + name, import.meta.url));
      return new Response(raw, {headers: {'Content-Type': name.endsWith('.html') ? 'text/html; charset=utf-8' : 'text/plain'}});
    }},
    outboundService: async request => {
      assert.equal(new URL(request.url).hostname, 'api.resend.com');
      const data = await request.json();
      messages.push({identity: data.to[0], code: data.text.match(/\b\d{6}\b/)[0]});
      return new Response(JSON.stringify({id: 'synthetic'}), {status: rejectDelivery ? 500 : 200});
    }
  });
  db = await mf.getD1Database('DB');
  const schema = await readFile(new URL('../migrations/0001_accounts.sql', import.meta.url), 'utf8');
  // D1 exec splits on lines; submit each complete migration statement instead.
  for (const sql of schema.replace(/^--.*$/gm, '').split(/;\s*\n/).filter(s => s.trim())) await db.prepare(sql).run();
});
after(async () => { await mf?.dispose(); });

test('email OTP creates account, stores only digests and cannot be replayed', async () => {
  const result = await login('First@Example.com');
  assert.match(result.token, /^[a-f0-9]{64}$/);
  const me = await call('me', {}, result.token);
  assert.equal(me.value.identity, 'first@example.com'); assert.deepEqual(me.value.licenses, []);
  const otp = await db.prepare('SELECT * FROM otp WHERE id=?').bind(result.challenge).first();
  assert.notEqual(otp.digest, result.code); assert.equal(otp.used, 1);
  const session = await db.prepare('SELECT * FROM sessions').first();
  assert.notEqual(session.digest, result.token);
  assert.equal((await call('otp/verify', {challenge: result.challenge, code: result.code})).status, 400);
});
test('portal session uses HttpOnly cookie without returning bearer token', async () => {
  const result = await call('otp/request', {identity: 'portal@example.com'});
  const verified = await call('otp/verify', {challenge: result.value.challenge, code: messages.at(-1).code});
  assert.equal(verified.status, 200); assert.equal(verified.value.token, undefined);
  const cookie = verified.headers.get('Set-Cookie'); assert.match(cookie, /HttpOnly/); assert.match(cookie, /SameSite=Strict/);
  const me = await call('me', {}, null, {Cookie: cookie.split(';')[0]}); assert.equal(me.status, 200);
  assert.equal((await call('logout', {}, null, {Cookie: cookie.split(';')[0]})).status, 200);
  assert.equal((await call('me', {}, null, {Cookie: cookie.split(';')[0]})).status, 401);
});
test('OTP expires and five wrong attempts lock it even with the correct code', async () => {
  const result = await call('otp/request', {identity: 'attempts@example.com'});
  const code = messages.at(-1).code, wrong = code === '000000' ? '111111' : '000000';
  for (let i = 0; i < 5; i++) assert.equal((await call('otp/verify', {challenge: result.value.challenge, code: wrong})).status, 400);
  assert.equal((await call('otp/verify', {challenge: result.value.challenge, code})).status, 400);
  const expired = await call('otp/request', {identity: 'expired-otp@example.com'});
  await db.prepare('UPDATE otp SET expires=0 WHERE id=?').bind(expired.value.challenge).run();
  assert.equal((await call('otp/verify', {challenge: expired.value.challenge, code: messages.at(-1).code})).status, 400);
});
test('parallel OTP redemption grants exactly one session', async () => {
  const result = await call('otp/request', {identity: 'race-otp@example.com'});
  const body = {challenge: result.value.challenge, code: messages.at(-1).code};
  const results = await Promise.all([call('otp/verify', body), call('otp/verify', body)]);
  assert.deepEqual(results.map(r => r.status).sort(), [200, 400]);
});
test('delivery failure invalidates OTP; responses never contain the code', async () => {
  rejectDelivery = true;
  try {
    const result = await call('otp/request', {identity: 'delivery@example.com'});
    assert.equal(result.status, 503); assert.ok(!JSON.stringify(result.value).includes(messages.at(-1).code));
    const row = await db.prepare('SELECT * FROM otp WHERE identity=?').bind('delivery@example.com').first(); assert.equal(row.used, 1);
  } finally { rejectDelivery = false; }
});
test('rate limits prevent repeated email and SMS is disabled without configuration', async () => {
  assert.equal((await call('otp/request', {identity: 'limit@example.com'})).status, 200);
  assert.equal((await call('otp/request', {identity: 'limit@example.com'})).status, 429);
  assert.equal((await call('otp/request', {identity: '+84901234567'})).status, 503);
  assert.equal((await call('otp/request', {identity: '0901234567'})).status, 400);
});
test('verification grants no license; only admin can grant a purchase', async () => {
  const {token} = await login('purchase@example.com');
  assert.equal((await call('admin/grant', {identity: 'purchase@example.com', days: 30, device_limit: 1}, token)).status, 403);
  assert.equal((await call('licenses/key', {license_id: 'unpaid'}, token)).status, 409);
  assert.equal((await call('me', {}, token)).value.licenses.length, 0);
});
test('one-time key display and activation are atomic; raw key is not stored', async () => {
  const {token} = await login('key@example.com'), id = await grant('key@example.com');
  const issued = await Promise.all([call('licenses/key', {license_id: id}, token), call('licenses/key', {license_id: id}, token)]);
  assert.deepEqual(issued.map(r => r.status).sort(), [200, 409]);
  const key = issued.find(r => r.status === 200).value.key; assert.match(key, /^CZ-[A-F0-9]{40}$/);
  const row = await db.prepare('SELECT * FROM licenses WHERE id=?').bind(id).first(); assert.ok(!JSON.stringify(row).includes(key));
  const redeemed = await Promise.all([call('licenses/redeem', {key}, token), call('licenses/redeem', {key}, token)]);
  // Both requests come from the owner: one activates, the other gets that same activation back.
  assert.deepEqual(redeemed.map(r => r.status), [200, 200]);
  assert.deepEqual(redeemed[0].value, redeemed[1].value);
  const retried = await call('licenses/redeem', {key}, token);
  assert.equal(retried.status, 200); assert.equal(retried.value.expires, redeemed[0].value.expires);
  const me = await call('me', {}, token); assert.equal(me.value.licenses[0].status, 'active'); assert.ok(!JSON.stringify(me.value).includes(key));
});
test('admin reissue replaces a lost unredeemed key with audit; redeemed keys stay', async () => {
  const {token} = await login('lost@example.com'), id = await grant('lost@example.com');
  assert.equal((await call('admin/reissue', {license_id: id}, admin)).status, 409);
  const lost = (await call('licenses/key', {license_id: id}, token)).value.key;
  assert.equal((await call('admin/reissue', {license_id: id}, token)).status, 403);
  assert.equal((await call('admin/reissue', {license_id: id}, admin)).status, 200);
  assert.equal((await call('licenses/redeem', {key: lost}, token)).status, 409);
  const fresh = await call('licenses/key', {license_id: id}, token);
  assert.equal(fresh.status, 200); assert.notEqual(fresh.value.key, lost);
  assert.equal((await call('licenses/redeem', {key: fresh.value.key}, token)).status, 200);
  assert.equal((await call('admin/reissue', {license_id: id}, admin)).status, 409);
  const audit = await db.prepare("SELECT count(*) AS n FROM audit WHERE action='reissue' AND license_id=?").bind(id).first();
  assert.equal(audit.n, 1);
});
test('other accounts cannot take keys, redeem, remove devices or use another license', async () => {
  const a = await active('owner@example.com'), b = await login('other@example.com');
  assert.equal((await call('licenses/key', {license_id: a.id}, b.token)).status, 409);
  assert.equal((await call('licenses/redeem', {key: a.key}, b.token)).status, 409);
  const device_id = 'a'.repeat(32);
  assert.equal((await call('devices/activate', {license_id: a.id, device_id, name: 'Laptop'}, a.token)).status, 200);
  assert.equal((await call('devices/activate', {license_id: a.id, device_id, name: 'Laptop'}, b.token)).status, 403);
  await call('devices/remove', {license_id: a.id, device_id}, b.token);
  assert.equal((await call('licenses/check', {license_id: a.id, device_id}, a.token)).status, 200);
  const pending = await grant('owner@example.com');
  const key = (await call('licenses/key', {license_id: pending}, a.token)).value.key;
  assert.equal((await call('licenses/redeem', {key}, b.token)).status, 409);
});
test('parallel device activation enforces capacity; own device is idempotent', async () => {
  const {token, id} = await active('devices@example.com', 1);
  const one = {license_id: id, device_id: '1'.repeat(32), name: 'Laptop'}, two = {...one, device_id: '2'.repeat(32)};
  const results = await Promise.all([call('devices/activate', one, token), call('devices/activate', two, token)]);
  assert.deepEqual(results.map(r => r.status).sort(), [200, 409]);
  const winner = results[0].status === 200 ? one : two;
  assert.equal((await call('devices/activate', winner, token)).status, 200);
  assert.equal((await call('devices/remove', winner, token)).status, 200);
  assert.equal((await call('licenses/check', winner, token)).status, 403);
  assert.equal((await call('devices/activate', two, token)).status, 200);
});
test('expiry, revocation and logout deny further access', async () => {
  const a = await active('revoked@example.com'), data = {license_id: a.id, device_id: '3'.repeat(32), name: 'PC'};
  await call('devices/activate', data, a.token);
  await call('admin/revoke', {license_id: a.id}, admin);
  assert.equal((await call('licenses/check', data, a.token)).status, 403);
  assert.equal((await call('devices/activate', data, a.token)).status, 403);
  const b = await active('expired-license@example.com');
  await db.prepare('UPDATE licenses SET expires=0 WHERE id=?').bind(b.id).run();
  assert.equal((await call('devices/activate', {...data, license_id: b.id}, b.token)).status, 403);
  await call('logout', {}, a.token); assert.equal((await call('me', {}, a.token)).status, 401);
});
test('host, origin, content type, oversized body and asset access are checked', async () => {
  assert.equal((await call('otp/request', {identity: 'origin@example.com'}, null, {Origin: 'https://evil.example'})).status, 403);
  assert.equal((await mf.dispatchFetch('http://evil.example/health')).status, 403);
  assert.equal((await mf.dispatchFetch('http://localhost/api/me', {method: 'POST', body: '{}'})).status, 415);
  assert.equal((await call('me', {large: 'x'.repeat(9000)})).status, 413);
  assert.equal((await mf.dispatchFetch('http://localhost/app.js')).status, 404);
  const page = await mf.dispatchFetch('http://localhost/'); assert.equal(page.status, 200);
  assert.ok(!(await page.text()).includes('__TOKEN__'));
});
