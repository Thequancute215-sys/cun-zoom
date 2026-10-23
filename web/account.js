'use strict';
const el = id => document.getElementById(id);
const desktop = document.querySelector('meta[name="account-mode"]').content === 'desktop';
const appToken = document.querySelector('meta[name="app-token"]').content;
let challenge = '', recipient = '', messageTimer;
function notice(text, error = false) { clearTimeout(messageTimer); el('feedback').textContent = text; el('feedback').classList.toggle('error', error); el('feedback').hidden = false; messageTimer = setTimeout(() => el('feedback').hidden = true, 10000); }
async function api(path, data = {}) {
  const headers = {'Content-Type': 'application/json'};
  if (desktop) headers['X-App-Token'] = appToken;
  const response = await fetch((desktop ? '/account/' : '/api/') + path, {method: 'POST', headers, credentials: 'same-origin', body: JSON.stringify(data)});
  const result = await response.json();
  if (!response.ok || result.error) throw new Error(result.error || 'Chưa thực hiện được. Thử lại sau.');
  return result;
}
function busy(handler) { return async event => { event?.preventDefault(); const button = event?.submitter || event?.currentTarget; if (button) button.disabled = true; try { await handler(); } catch (error) { notice(error.message, true); } finally { if (button) button.disabled = false; } }; }
function button(text, action, secondary = false) { const item = document.createElement('button'); item.textContent = text; item.type = 'button'; if (secondary) item.className = 'secondary'; item.onclick = busy(action); return item; }
function text(tag, content, cls) { const item = document.createElement(tag); item.textContent = content; if (cls) item.className = cls; return item; }
function clearKey() { el('one-time-key').value = ''; el('license-key').value = ''; el('key-result').hidden = true; }
async function refresh() {
  const account = await api('me');
  el('login').hidden = true; el('dashboard').hidden = false; el('account-identity').textContent = account.identity;
  el('download').hidden = !account.download_url;
  if (account.download_url) { const u = new URL(account.download_url); if (u.protocol === 'https:') el('download').href = u.href; }
  el('open-app').hidden = true;
  if (desktop) { const state = await api('status'); el('open-app').hidden = !state.active; }
  el('licenses').replaceChildren();
  if (!account.licenses.length) el('licenses').append(text('p', 'Bạn chưa được cấp bản quyền. Sau khi mua, người bán sẽ cấp gói vào đúng email/SĐT này.'));
  const labels = {pending: 'Chờ lấy mã', issued: 'Đã cấp mã', active: 'Đang sử dụng', expired: 'Đã hết hạn', revoked: 'Đã thu hồi'};
  for (const license of account.licenses) {
    const card = text('article', '', 'card'), head = text('div', '', 'license-head');
    head.append(text('h2', `Gói ${license.days} ngày`), text('span', labels[license.status] || license.status, 'pill')); card.append(head);
    card.append(text('p', `${license.devices.length}/${license.device_limit} thiết bị`));
    if (license.expires) card.append(text('p', 'Hạn sử dụng: ' + new Date(license.expires * 1000).toLocaleString('vi-VN')));
    if (license.status === 'pending') card.append(button('Lấy mã · chỉ hiển thị một lần', async () => {
      const result = await api('licenses/key', {license_id: license.id});
      el('one-time-key').value = result.key; el('key-result').hidden = false;
      await refresh(); el('key-result').scrollIntoView({behavior: 'smooth', block: 'center'}); el('one-time-key').focus();
    }));
    if (license.status === 'issued') card.append(text('p', 'Mã đã hiển thị một lần. Nhập mã đã lưu bên dưới. Nếu mất mã, liên hệ người bán để thu hồi và cấp lại.', 'help'));
    if (license.status === 'active' && desktop) card.append(button('Dùng trên máy này', async () => { await api('devices/activate', {license_id: license.id}); location.assign('/'); }));
    for (const device of license.devices) {
      const row = text('div', '', 'device'); row.append(text('span', device.name));
      row.append(button('Gỡ thiết bị', async () => {
        if (!confirm(`Gỡ “${device.name}”? Máy này sẽ cần kích hoạt lại.`)) return;
        await api('devices/remove', {license_id: license.id, device_id: device.id}); await refresh();
      }, true)); card.append(row);
    }
    el('licenses').append(card);
  }
}
el('identity-form').onsubmit = busy(async () => {
  recipient = el('identity').value.trim(); const result = await api('otp/request', {identity: recipient}); challenge = result.challenge;
  el('identity-form').hidden = true; el('otp-form').hidden = false; el('otp').value = ''; el('otp-recipient').textContent = 'Mã xác minh đã gửi tới ' + recipient; el('otp').focus();
});
el('otp-form').onsubmit = busy(async () => { await api('otp/verify', {challenge, code: el('otp').value.trim()}); el('otp').value = ''; challenge = ''; await refresh(); });
el('back').onclick = () => { challenge = ''; el('otp').value = ''; el('otp-form').hidden = true; el('identity-form').hidden = false; el('identity').focus(); };
el('logout').onclick = busy(async () => { await api('logout'); clearKey(); location.reload(); });
el('reload').onclick = busy(refresh);
el('redeem-form').onsubmit = busy(async () => { await api('licenses/redeem', {key: el('license-key').value.trim()}); clearKey(); await refresh(); notice('Đã kích hoạt bản quyền.'); });
el('use-key').onclick = busy(async () => { await api('licenses/redeem', {key: el('one-time-key').value}); clearKey(); await refresh(); notice('Đã kích hoạt bản quyền.'); });
el('copy-key').onclick = busy(async () => { await navigator.clipboard.writeText(el('one-time-key').value); notice('Đã sao chép. Hãy lưu mã ở nơi riêng tư.'); });
el('hide-key').onclick = () => { if (confirm('Bạn đã lưu mã? Mã sẽ không được hiển thị lại.')) clearKey(); };
window.addEventListener('pagehide', clearKey);
refresh().catch(() => { el('login').hidden = false; el('dashboard').hidden = true; });
