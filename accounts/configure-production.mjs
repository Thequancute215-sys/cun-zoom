/** Generate public production configuration. Credentials are never written here. */
import {parseArgs} from 'node:util';
import {mkdir, writeFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {resolve} from 'node:path';

const root = fileURLToPath(new URL('.', import.meta.url));
try {
  const {values} = parseArgs({options: {
    origin: {type: 'string'}, database: {type: 'string'}, sender: {type: 'string'},
    download: {type: 'string'}, name: {type: 'string'}, output: {type: 'string'}
  }});
  const origin = values.origin || process.env.ACCOUNTS_PUBLIC_ORIGIN;
  const database = values.database || process.env.ACCOUNTS_D1_DATABASE_ID;
  const sender = values.sender || process.env.ACCOUNTS_EMAIL_FROM;
  const download = values.download || process.env.ACCOUNTS_DOWNLOAD_URL;
  const name = values.name || process.env.ACCOUNTS_WORKER_NAME || 'cun-zoom-accounts';
  const parsed = new URL(origin);
  if (parsed.protocol !== 'https:' || parsed.origin !== origin || parsed.username || parsed.password) throw new Error('Production origin must be an HTTPS origin without a path, credentials or trailing slash.');
  if (!/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i.test(database || '')) throw new Error('Provide the actual D1 database UUID.');
  if (typeof sender !== 'string' || sender.length > 254 || /[\r\n]/.test(sender) || !/[^\s<>@]+@[^\s<>@]+\.[^\s<>@]+/.test(sender)) throw new Error('Provide an email sender verified by Resend.');
  const artifact = new URL(download);
  if (artifact.protocol !== 'https:' || artifact.username || artifact.password) throw new Error('Provide an HTTPS download link for the commercial application.');
  if (!/^[a-z0-9][a-z0-9-]{0,62}$/.test(name)) throw new Error('Worker name must use lowercase ASCII letters, numbers and hyphens.');
  const output = values.output ? resolve(values.output) : resolve(root, '.wrangler/production.json');
  const config = {
    name, main: resolve(root, 'worker.mjs'), compatibility_date: '2026-08-01',
    workers_dev: true,
    assets: {directory: resolve(root, '../web'), binding: 'ASSETS', run_worker_first: true},
    d1_databases: [{binding: 'DB', database_name: 'cun-zoom-accounts', database_id: database, migrations_dir: resolve(root, 'migrations')}],
    vars: {PUBLIC_ORIGIN: origin, EMAIL_FROM: sender, SMS_ENABLED: 'false', OTP_DAILY_LIMIT: '100', DOWNLOAD_URL: download},
    observability: {enabled: false}
  };
  await mkdir(resolve(output, '..'), {recursive: true});
  await writeFile(output, JSON.stringify(config, null, 2) + '\n', {mode: 0o600});
  console.log('Production configuration generated; no credentials were written.');
} catch (error) {
  console.error(error instanceof TypeError ? 'Required production settings are missing or contain invalid URLs.' : error.message);
  process.exitCode = 1;
}
