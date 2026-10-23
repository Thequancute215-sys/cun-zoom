/** Local operator CLI. ADMIN_TOKEN comes from the environment, never an argument. */
import {parseArgs} from 'node:util';
const {values, positionals} = parseArgs({allowPositionals: true, options: {
  url: {type: 'string'}, identity: {type: 'string'}, days: {type: 'string', default: '30'},
  devices: {type: 'string', default: '1'}, license: {type: 'string'}
}});
try {
  if (!process.env.ADMIN_TOKEN || process.env.ADMIN_TOKEN.length < 32) throw new Error('Set ADMIN_TOKEN securely in this shell. Do not put it in command arguments.');
  const url = new URL(values.url);
  if (url.protocol !== 'https:' && !['localhost', '127.0.0.1'].includes(url.hostname)) throw new Error('Use an HTTPS account service.');
  if (url.username || url.password || url.pathname !== '/' || url.search || url.hash) throw new Error('Use an origin without credentials or path.');
  const operation = positionals[0];
  if (!['grant', 'revoke'].includes(operation)) throw new Error('Usage: node admin.mjs grant --url ORIGIN --identity EMAIL_OR_PHONE --days 30 --devices 1 | revoke --url ORIGIN --license ID');
  const data = operation === 'grant' ? {identity: values.identity, days: Number(values.days), device_limit: Number(values.devices)} : {license_id: values.license};
  const response = await fetch(url.origin + '/api/admin/' + operation, {method: 'POST', redirect: 'error', signal: AbortSignal.timeout(15000),
    headers: {'Content-Type': 'application/json', Authorization: 'Bearer ' + process.env.ADMIN_TOKEN}, body: JSON.stringify(data)});
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || 'Operation failed.');
  console.log(JSON.stringify(result, null, 2));
} catch (error) { console.error(error.message); process.exitCode = 1; }
