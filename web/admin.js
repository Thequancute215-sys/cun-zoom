'use strict';
// Seller console for the account service: orders to approve, licences, plans, audit and sales charts.
// Same-origin API with the HttpOnly session cookie; every value reaches the page through textContent.
const el = id => document.getElementById(id);
const SVG = 'http://www.w3.org/2000/svg';
let messageTimer, challenge = '', days = 30, overviewData = null, editingPlan = null;
const cursors = {orders: null, licenses: null};
const ORDER = {pending: ['Chờ duyệt', 'warning'], approved: ['Đã duyệt', 'good'], rejected: ['Từ chối', 'critical'], cancelled: ['Khách hủy', '']};
const LICENSE = {active: ['Đang dùng', 'good'], issued: ['Đã phát mã', 'warning'], pending: ['Chờ lấy mã', 'warning'], expired: ['Hết hạn', ''], revoked: ['Đã thu hồi', 'critical']};
const ACTION = {grant: 'Cấp gói', revoke: 'Thu hồi', reissue: 'Cấp lại mã', approve: 'Duyệt đơn', reject: 'Từ chối đơn', plan: 'Lưu gói'};
// Fixed series order (validated palette slots 1-3); a series keeps its colour whatever else is shown.
const ORDER_SERIES = [{key: 'approved', label: 'Đã duyệt', cls: 's-approved', swatch: 'key-approved'},
  {key: 'pending', label: 'Chờ duyệt', cls: 's-pending', swatch: 'key-pending'},
  {key: 'closed', label: 'Từ chối/khách hủy', cls: 's-closed', swatch: 'key-closed'}];

function node(tag, text, cls) { const item = document.createElement(tag); if (text !== undefined && text !== null) item.textContent = text; if (cls) item.className = cls; return item; }
function notice(text, error = false) { clearTimeout(messageTimer); const box = el('feedback'); box.textContent = text; box.classList.toggle('error', error); box.hidden = false; messageTimer = setTimeout(() => box.hidden = true, 8000); }
async function api(path, data = {}) {
  const response = await fetch('/api/' + path, {method: 'POST', headers: {'Content-Type': 'application/json'}, credentials: 'same-origin', body: JSON.stringify(data)});
  const result = await response.json().catch(() => ({}));
  if (path.startsWith('admin/') && (response.status === 401 || response.status === 403)) { showLogin(); throw new Error(result.error || 'Cần đăng nhập quản trị.'); }
  if (!response.ok) throw new Error(result.error || 'Chưa thực hiện được. Thử lại sau.');
  return result;
}
function busy(handler) { return async event => { event?.preventDefault(); const button = event?.submitter || event?.currentTarget; if (button) button.disabled = true; try { await handler(event); } catch (error) { notice(error.message, true); } finally { if (button) button.disabled = false; } }; }
const money = n => new Intl.NumberFormat('vi-VN').format(n) + ' đ';
const one = v => (Math.round(v * 10) / 10).toString().replace('.', ',');
const compact = n => n >= 1e9 ? one(n / 1e9) + ' tỷ' : n >= 1e6 ? one(n / 1e6) + ' tr' : n >= 1e3 ? one(n / 1e3) + 'k' : String(n);
const when = s => s ? new Date(s * 1000).toLocaleString('vi-VN', {day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit'}) : '—';
const dayLabel = d => d.slice(8, 10) + '/' + d.slice(5, 7);
const dayLong = d => dayLabel(d) + '/' + d.slice(0, 4);
function pill(map, state) { const [label, tone] = map[state] || [state, '']; return node('span', label, 'pill ' + tone); }
function button(text, action, cls = 'small') { const item = node('button', text, cls); item.type = 'button'; item.onclick = busy(action); return item; }
function cell(row, content, cls) { const td = node('td', typeof content === 'string' || typeof content === 'number' ? content : undefined, cls); if (content instanceof Node) td.append(content); row.append(td); return td; }
function stacked(main, sub) { const box = document.createDocumentFragment(); box.append(main instanceof Node ? main : node('span', main)); if (sub) box.append(node('span', sub, 'sub')); return box; }
function emptyRow(tbody, columns, text) { const row = node('tr', undefined, 'empty-row'); const td = node('td', text); td.colSpan = columns; row.append(td); tbody.append(row); }

// --- Sign-in -----------------------------------------------------------------------------------------
function showLogin() { el('console').hidden = true; el('login').hidden = false; el('logout').hidden = true; el('who').textContent = ''; }
async function start() {
  try {
    const me = await api('admin/me');
    el('who').textContent = me.identity === 'cli' ? 'CLI quản trị' : me.identity;
    el('logout').hidden = false; el('login').hidden = true; el('console').hidden = false;
    tab(location.hash.slice(1));
    return true;
  } catch { showLogin(); return false; }
}
el('identity-form').onsubmit = busy(async () => {
  const result = await api('otp/request', {identity: el('identity').value.trim()}); challenge = result.challenge;
  el('identity-form').hidden = true; el('otp-form').hidden = false; el('otp').value = ''; el('otp').focus();
});
el('otp-form').onsubmit = busy(async () => {
  await api('otp/verify', {challenge, code: el('otp').value.trim(), client: 'portal'}); challenge = '';
  if (!await start()) notice('Tài khoản này không có quyền quản trị. Kiểm tra ADMIN_IDENTITIES của dịch vụ.', true);
});
el('back').onclick = () => { challenge = ''; el('otp-form').hidden = true; el('identity-form').hidden = false; el('identity').focus(); };
el('logout').onclick = busy(async () => { await api('logout'); location.replace('/admin'); });
el('theme').onclick = () => {
  const dark = document.documentElement.dataset.theme ? document.documentElement.dataset.theme === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
  document.documentElement.dataset.theme = dark ? 'light' : 'dark';
  try { localStorage.setItem('cz-admin-theme', document.documentElement.dataset.theme); } catch {}
  if (overviewData) paintCharts();
};
try { const saved = localStorage.getItem('cz-admin-theme'); if (saved === 'light' || saved === 'dark') document.documentElement.dataset.theme = saved; } catch {}

// --- Tabs --------------------------------------------------------------------------------------------
const loaders = {overview: loadOverview, orders: () => loadOrders(true), licenses: () => loadLicenses(true), plans: loadPlans, audit: loadAudit};
function tab(name) {
  if (!loaders[name]) name = 'overview';
  el('tooltip').hidden = true;
  document.querySelectorAll('[data-tab]').forEach(b => b.setAttribute('aria-selected', String(b.dataset.tab === name)));
  document.querySelectorAll('[data-pane]').forEach(p => p.hidden = p.dataset.pane !== name);
  if (location.hash !== '#' + name) history.replaceState(null, '', '#' + name);
  loaders[name]().catch(error => notice(error.message, true));
  if (name !== 'overview') refreshBadge();
}
document.querySelectorAll('[data-tab]').forEach(b => b.onclick = () => tab(b.dataset.tab));
addEventListener('hashchange', () => { if (!el('console').hidden) tab(location.hash.slice(1)); });
el('tile-pending').onclick = () => { el('order-status').value = 'pending'; tab('orders'); };

// --- Overview and charts ------------------------------------------------------------------------------
async function refreshBadge() {
  try { overviewData = await api('admin/overview', {days}); badge(); } catch {}
}
function badge() { const n = overviewData.orders.pending; el('pending-badge').hidden = !n; el('pending-badge').textContent = n; }
async function loadOverview() { overviewData = await api('admin/overview', {days}); badge(); paintOverview(); }
document.querySelectorAll('[data-days]').forEach(b => b.onclick = busy(async () => {
  days = Number(b.dataset.days);
  document.querySelectorAll('[data-days]').forEach(x => x.setAttribute('aria-pressed', String(x === b)));
  await loadOverview();
}));
function paintOverview() {
  const o = overviewData;
  el('stat-pending').textContent = o.orders.pending;
  el('stat-revenue').textContent = money(o.totals.revenue);
  el('stat-sales').textContent = o.totals.sales + ' đơn đã duyệt trong ' + o.days + ' ngày';
  el('stat-active').textContent = o.licenses.active;
  el('stat-issued').textContent = (o.licenses.issued + o.licenses.pending) + ' gói chưa kích hoạt';
  el('stat-users').textContent = o.totals.new_users;
  el('stat-total-users').textContent = 'trong ' + o.days + ' ngày · tổng ' + o.totals.users + ' tài khoản';
  el('stat-devices').textContent = o.totals.active_devices;
  const legend = el('legend-orders'); legend.replaceChildren();
  for (const s of ORDER_SERIES) { const item = node('span'); item.append(node('i', '', s.swatch), s.label); legend.append(item); }
  paintCharts();
  table('table-revenue', ['Ngày', 'Doanh thu', 'Số đơn duyệt'], o.series.map(d => [dayLong(d.date), money(d.revenue), d.sales]));
  table('table-orders', ['Ngày', ...ORDER_SERIES.map(s => s.label)], o.series.map(d => [dayLong(d.date), ...ORDER_SERIES.map(s => d[s.key])]));
  table('table-users', ['Ngày', 'Người dùng mới'], o.series.map(d => [dayLong(d.date), d.users]));
  table('table-licenses', ['Trạng thái', 'Số gói'], licenceItems().map(i => [i.label, i.value]));
}
const licenceItems = () => Object.keys(LICENSE).map(k => ({label: LICENSE[k][0], value: overviewData.licenses[k]}));
function paintCharts() {
  const o = overviewData;
  columns('chart-revenue', o.series, [{key: 'revenue', label: 'Doanh thu', cls: 's-one'}], {format: money, tick: compact, integer: false, title: 'Doanh thu đã duyệt theo ngày'});
  columns('chart-orders', o.series, ORDER_SERIES, {format: String, tick: String, integer: true, title: 'Đơn hàng mới theo ngày, theo trạng thái'});
  line('chart-users', o.series, 'users', 'Người dùng mới');
  hbars('chart-licenses', licenceItems());
}
function table(id, headers, rows) {
  const wrap = el(id), tableNode = node('table'), head = node('tr'), body = node('tbody');
  headers.forEach((h, i) => head.append(node('th', h, i ? 'num' : '')));
  for (const row of rows) { const tr = node('tr'); row.forEach((v, i) => tr.append(node('td', String(v), i ? 'num' : ''))); body.append(tr); }
  const thead = node('thead'); thead.append(head); tableNode.append(thead, body); wrap.replaceChildren(tableNode);
}
function svg(tag, attrs, parent) { const item = document.createElementNS(SVG, tag); for (const [k, v] of Object.entries(attrs || {})) item.setAttribute(k, v); if (parent) parent.append(item); return item; }
function niceNumber(x) { const p = 10 ** Math.floor(Math.log10(x)), f = x / p; return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10) * p; }
function scale(max, integer) {
  let step = niceNumber(max / 4); if (integer) step = Math.max(1, Math.ceil(step));
  const top = step * Math.max(1, Math.ceil(max / step)), ticks = [];
  for (let t = 0; t <= top + step / 2; t += step) ticks.push(t);
  return {top, ticks};
}
// Columns: 4px rounded data end, square at the baseline, at most 24px wide, 2px surface gap between stacked parts.
function topRounded(x, y, w, h, r) { if (h <= 0) return ''; r = Math.min(r, w / 2, h); return `M${x},${y + h}V${y + r}Q${x},${y} ${x + r},${y}H${x + w - r}Q${x + w},${y} ${x + w},${y + r}V${y + h}Z`; }
function rightRounded(x, y, w, h, r) { if (w <= 0) return ''; r = Math.min(r, h / 2, w); return `M${x},${y}H${x + w - r}Q${x + w},${y} ${x + w},${y + r}V${y + h - r}Q${x + w},${y + h} ${x + w - r},${y + h}H${x}Z`; }
function frame(id, rows, right = 12) {
  const host = el(id); host.replaceChildren();
  const W = Math.max(300, host.clientWidth || 600), H = 220, m = {l: 52, r: right, t: 14, b: 28};
  return {host, W, H, m, iw: W - m.l - m.r, ih: H - m.t - m.b, band: (W - m.l - m.r) / rows.length};
}
function axes(root, f, s, tick, rows) {
  for (const t of s.ticks) {
    const y = f.m.t + f.ih - t / s.top * f.ih;
    svg('line', {x1: f.m.l, x2: f.W - f.m.r, y1: y, y2: y, class: t ? 'grid' : 'baseline'}, root);
    svg('text', {x: f.m.l - 8, y: y + 4, 'text-anchor': 'end', class: 'tick'}, root).textContent = tick(t);
  }
  // Evenly spaced day labels plus the last day; a regular label too close to the last one is dropped.
  const every = Math.ceil(rows.length / Math.max(2, Math.floor(f.iw / 56))), last = rows.length - 1;
  rows.forEach((r, i) => {
    if (i !== last && (i % every || (last - i) * f.band < 48)) return;
    svg('text', {x: f.m.l + f.band * i + f.band / 2, y: f.H - 8, 'text-anchor': 'middle', class: 'tick'}, root).textContent = dayLabel(r.date);
  });
}
function hover(root, f, rows, describe, onMove) {
  rows.forEach((r, i) => {
    const hit = svg('rect', {x: f.m.l + f.band * i, y: f.m.t, width: f.band, height: f.ih, class: 'hit'}, root);
    hit.addEventListener('pointermove', event => { tip(event, ...describe(r)); onMove?.(i); });
    hit.addEventListener('pointerleave', () => { el('tooltip').hidden = true; onMove?.(-1); });
  });
}
function columns(id, rows, series, opts) {
  const f = frame(id, rows), total = r => series.reduce((sum, s) => sum + r[s.key], 0), max = Math.max(0, ...rows.map(total));
  if (!max) { f.host.append(node('div', 'Chưa có dữ liệu trong khoảng này.', 'empty')); return; }
  const s = scale(max, opts.integer), root = svg('svg', {viewBox: `0 0 ${f.W} ${f.H}`, role: 'img', 'aria-label': opts.title + '. Xem bảng số liệu bên dưới.'}, f.host);
  axes(root, f, s, opts.tick, rows);
  hover(root, f, rows, r => [dayLong(r.date), series.map(x => [x.label, opts.format(r[x.key]), x.swatch])]);
  const width = Math.min(24, Math.max(2, f.band * 0.62));
  rows.forEach((r, i) => {
    const x = f.m.l + f.band * i + (f.band - width) / 2, parts = series.filter(x => r[x.key] > 0);
    let base = f.m.t + f.ih;
    parts.forEach((part, j) => {
      const h = r[part.key] / s.top * f.ih, gap = j ? 2 : 0;
      svg('path', {d: topRounded(x, base - h, width, h - gap, j === parts.length - 1 ? 4 : 0), class: part.cls}, root);
      base -= h;
    });
  });
  // Label only the peak day, so the axis and the table carry the rest.
  const peak = rows.reduce((best, r, i) => total(r) > total(rows[best]) ? i : best, 0);
  svg('text', {x: f.m.l + f.band * peak + f.band / 2, y: f.m.t + f.ih - total(rows[peak]) / s.top * f.ih - 6, 'text-anchor': 'middle', class: 'value'}, root).textContent = opts.tick(total(rows[peak]));
}
function line(id, rows, key, label) {
  const f = frame(id, rows, 28), max = Math.max(0, ...rows.map(r => r[key]));
  if (!max) { f.host.append(node('div', 'Chưa có dữ liệu trong khoảng này.', 'empty')); return; }
  const s = scale(max, true), root = svg('svg', {viewBox: `0 0 ${f.W} ${f.H}`, role: 'img', 'aria-label': label + ' theo ngày. Xem bảng số liệu bên dưới.'}, f.host);
  axes(root, f, s, String, rows);
  const x = i => f.m.l + f.band * i + f.band / 2, y = v => f.m.t + f.ih - v / s.top * f.ih;
  const points = rows.map((r, i) => `${x(i)},${y(r[key])}`).join(' L');
  const cross = svg('line', {y1: f.m.t, y2: f.m.t + f.ih, class: 'cross', visibility: 'hidden'}, root);
  hover(root, f, rows, r => [dayLong(r.date), [[label, String(r[key])]]], i => {
    cross.setAttribute('visibility', i < 0 ? 'hidden' : 'visible'); if (i >= 0) { cross.setAttribute('x1', x(i)); cross.setAttribute('x2', x(i)); }
  });
  svg('path', {d: `M${x(0)},${f.m.t + f.ih} L${points} L${x(rows.length - 1)},${f.m.t + f.ih}Z`, class: 'area-one'}, root);
  svg('path', {d: 'M' + points, class: 'line-one'}, root);
  const last = rows.length - 1;
  svg('circle', {cx: x(last), cy: y(rows[last][key]), r: 4, class: 'dot-one'}, root);
  // The latest value sits right of the end dot, clear of the line.
  svg('text', {x: x(last) + 9, y: y(rows[last][key]) + 4, class: 'value'}, root).textContent = rows[last][key];
}
function hbars(id, items) {
  const host = el(id); host.replaceChildren();
  const max = Math.max(0, ...items.map(i => i.value));
  if (!max) { host.append(node('div', 'Chưa cấp bản quyền nào.', 'empty')); return; }
  const W = Math.max(300, host.clientWidth || 400), row = 36, labelW = 92, H = items.length * row + 4, valueW = 40;
  const iw = W - labelW - valueW, root = svg('svg', {viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': 'Bản quyền theo trạng thái. Xem bảng số liệu bên dưới.'}, host);
  const total = items.reduce((sum, i) => sum + i.value, 0);
  svg('line', {x1: labelW, x2: labelW, y1: 0, y2: H, class: 'baseline'}, root);
  items.forEach((item, i) => {
    const y = i * row + 4, w = item.value / max * iw;
    const hit = svg('rect', {x: 0, y, width: W, height: row - 4, class: 'hit'}, root);
    hit.addEventListener('pointermove', event => tip(event, item.label, [['Số gói', String(item.value)], ['Tỉ lệ', Math.round(item.value / total * 100) + '%']]));
    hit.addEventListener('pointerleave', () => el('tooltip').hidden = true);
    svg('text', {x: labelW - 10, y: y + row / 2 + 2, 'text-anchor': 'end', class: 'category'}, root).textContent = item.label;
    svg('path', {d: rightRounded(labelW, y + (row - 4 - 16) / 2, w, 16, 4), class: 's-one'}, root);
    svg('text', {x: labelW + w + 6, y: y + row / 2 + 2, class: 'value'}, root).textContent = item.value;
  });
}
function tip(event, title, lines) {
  const box = el('tooltip'); box.replaceChildren(node('b', title));
  for (const [label, value, swatch] of lines) { const row = node('div'), left = node('span'); if (swatch) left.append(node('i', '', swatch)); left.append(label); row.append(left, node('span', value)); box.append(row); }
  box.hidden = false;
  box.style.left = Math.min(event.clientX + 14, innerWidth - box.offsetWidth - 8) + 'px';
  box.style.top = Math.min(event.clientY + 14, innerHeight - box.offsetHeight - 8) + 'px';
}
let resizeTimer;
addEventListener('resize', () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(() => { if (overviewData && !el('console').hidden) paintCharts(); }, 150); });

// --- Orders ------------------------------------------------------------------------------------------
async function loadOrders(reset) {
  const tbody = el('orders').tBodies[0];
  if (reset) { cursors.orders = null; tbody.replaceChildren(); }
  const result = await api('admin/orders', {status: el('order-status').value, query: el('order-query').value, before: cursors.orders});
  for (const o of result.orders) {
    const row = node('tr');
    cell(row, o.code, 'code');
    cell(row, o.identity);
    cell(row, stacked(o.plan_name, o.days + ' ngày · ' + o.device_limit + ' máy'));
    cell(row, money(o.price), 'num');
    cell(row, o.note || '—', 'note');
    cell(row, stacked(when(o.created), o.decided ? 'Xử lý: ' + when(o.decided) : ''));
    cell(row, stacked(pill(ORDER, o.status), o.reason || (o.decided_by && o.status !== 'cancelled' ? 'bởi ' + o.decided_by : '')));
    const actions = cell(row, undefined, 'actions');
    if (o.status === 'pending') {
      actions.append(button('Duyệt', async () => {
        if (!confirm(`Duyệt đơn ${o.code}?\n${o.identity} · ${o.plan_name} · ${money(o.price)}\nSẽ cấp gói ${o.days} ngày, ${o.device_limit} máy.`)) return;
        await api('admin/orders/approve', {order_id: o.id}); notice('Đã duyệt ' + o.code + '. Khách đăng nhập để lấy mã bản quyền.');
        await loadOrders(true); refreshBadge();
      }, 'small'));
      actions.append(button('Từ chối', async () => {
        const reason = prompt(`Lý do từ chối đơn ${o.code} (khách sẽ thấy):`, 'Chưa nhận được thanh toán');
        if (reason === null) return;
        await api('admin/orders/reject', {order_id: o.id, reason}); notice('Đã từ chối ' + o.code + '.');
        await loadOrders(true); refreshBadge();
      }, 'small danger'));
    }
    tbody.append(row);
  }
  if (reset && !result.orders.length) emptyRow(tbody, 8, 'Không có đơn phù hợp.');
  const last = result.orders.at(-1);
  cursors.orders = last ? {created: last.created, id: last.id} : null;
  el('orders-more').hidden = result.orders.length < 50;
}
let searchTimer;
const debounce = job => () => { clearTimeout(searchTimer); searchTimer = setTimeout(() => job().catch(error => notice(error.message, true)), 300); };
el('order-status').onchange = () => loadOrders(true).catch(error => notice(error.message, true));
el('order-query').oninput = debounce(() => loadOrders(true));
el('orders-more').onclick = busy(() => loadOrders(false));

// --- Licences ----------------------------------------------------------------------------------------
async function loadLicenses(reset) {
  const tbody = el('licenses').tBodies[0];
  if (reset) { cursors.licenses = null; tbody.replaceChildren(); }
  const result = await api('admin/licenses', {status: el('license-status').value, query: el('license-query').value, before: cursors.licenses});
  for (const l of result.licenses) {
    const row = node('tr');
    cell(row, stacked(l.identity, 'Cấp ' + when(l.created)));
    cell(row, l.days + ' ngày · ' + l.device_limit + ' máy');
    cell(row, pill(LICENSE, l.status));
    cell(row, l.expires ? when(l.expires) : l.status === 'revoked' ? '—' : 'Tính từ lúc kích hoạt');
    cell(row, l.devices + '/' + l.device_limit, 'num');
    cell(row, l.order_code || '—', 'code');
    const actions = cell(row, undefined, 'actions');
    if (l.status === 'issued') actions.append(button('Cấp lại mã', async () => {
      if (!confirm(`Cấp mã mới cho ${l.identity}? Mã cũ chưa kích hoạt sẽ mất hiệu lực; khách đăng nhập để lấy mã mới.`)) return;
      await api('admin/reissue', {license_id: l.id}); notice('Mã cũ đã mất hiệu lực. Báo khách đăng nhập để lấy mã mới.'); await loadLicenses(true);
    }, 'small ghost'));
    if (l.status !== 'revoked') actions.append(button('Thu hồi', async () => {
      if (!confirm(`Thu hồi bản quyền của ${l.identity}? Các máy đang dùng sẽ không bắt đầu được việc mới; dữ liệu của khách vẫn giữ nguyên.`)) return;
      await api('admin/revoke', {license_id: l.id}); notice('Đã thu hồi.'); await loadLicenses(true);
    }, 'small danger'));
    tbody.append(row);
  }
  if (reset && !result.licenses.length) emptyRow(tbody, 7, 'Không có bản quyền phù hợp.');
  const last = result.licenses.at(-1);
  cursors.licenses = last ? {created: last.created, id: last.id} : null;
  el('licenses-more').hidden = result.licenses.length < 50;
}
el('license-status').onchange = () => loadLicenses(true).catch(error => notice(error.message, true));
el('license-query').oninput = debounce(() => loadLicenses(true));
el('licenses-more').onclick = busy(() => loadLicenses(false));
el('grant-form').onsubmit = busy(async () => {
  const identity = el('grant-identity').value.trim();
  const result = await api('admin/grant', {identity, days: Number(el('grant-days').value), device_limit: Number(el('grant-devices').value)});
  notice(`Đã cấp gói ${result.days} ngày cho ${result.identity}. Khách đăng nhập để lấy mã.`);
  el('grant-identity').value = ''; await loadLicenses(true);
});

// --- Plans -------------------------------------------------------------------------------------------
function editPlan(plan) {
  editingPlan = plan?.id || null;
  el('plan-title').textContent = plan ? 'Sửa gói “' + plan.name + '”' : 'Thêm gói';
  el('plan-name').value = plan?.name || ''; el('plan-days').value = plan?.days || 30; el('plan-devices').value = plan?.device_limit || 1;
  el('plan-price').value = plan?.price ?? 0; el('plan-active').checked = plan ? !!plan.active : true;
}
async function loadPlans() {
  const result = await api('admin/plans'), tbody = el('plans').tBodies[0]; tbody.replaceChildren();
  for (const p of result.plans) {
    const row = node('tr');
    cell(row, p.name); cell(row, p.days, 'num'); cell(row, p.device_limit, 'num'); cell(row, money(p.price), 'num');
    cell(row, node('span', p.active ? 'Đang mở bán' : 'Tạm ẩn', 'pill ' + (p.active ? 'good' : '')));
    cell(row, undefined, 'actions').append(button('Sửa', async () => { editPlan(p); el('plan-name').focus(); }, 'small ghost'));
    tbody.append(row);
  }
  if (!result.plans.length) emptyRow(tbody, 6, 'Chưa có gói nào. Thêm gói để khách đặt đơn.');
}
el('plan-form').onsubmit = busy(async () => {
  await api('admin/plans/save', {id: editingPlan, name: el('plan-name').value, days: Number(el('plan-days').value), device_limit: Number(el('plan-devices').value),
    price: Number(el('plan-price').value), active: el('plan-active').checked});
  notice('Đã lưu gói.'); editPlan(null); await loadPlans();
});
el('plan-reset').onclick = () => editPlan(null);

// --- Audit -------------------------------------------------------------------------------------------
async function loadAudit() {
  const result = await api('admin/audit'), tbody = el('audit').tBodies[0]; tbody.replaceChildren();
  for (const a of result.audit) {
    const row = node('tr');
    cell(row, when(a.created)); cell(row, !a.actor ? '—' : a.actor === 'cli' ? 'CLI quản trị' : a.actor); cell(row, ACTION[a.action] || a.action); cell(row, a.detail || '—', 'note');
    tbody.append(row);
  }
  if (!result.audit.length) emptyRow(tbody, 4, 'Chưa có thao tác nào.');
}

start();
