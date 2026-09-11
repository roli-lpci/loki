import { spawnSync } from 'node:child_process';

const result = spawnSync(
  process.platform === 'win32' ? 'npm.cmd' : 'npm',
  ['pack', '--dry-run', '--json'],
  { cwd: new URL('../', import.meta.url), encoding: 'utf8' },
);

if (result.status !== 0) {
  process.stderr.write(result.stderr || result.stdout || 'npm pack --dry-run failed\n');
  process.exit(result.status ?? 1);
}

let payload;
try {
  payload = JSON.parse(result.stdout);
} catch (error) {
  console.error('Could not parse npm pack --dry-run --json output.');
  console.error(result.stdout);
  throw error;
}

const files = payload?.[0]?.files ?? [];
const forbidden = files
  .map(file => file.path)
  .filter(path => (
    /(^|\/)__pycache__\//.test(path)
    || /\.py[co]$/.test(path)
    || /(^|\/)[^/]+\.egg-info\//.test(path)
    || /^MagicMock\//.test(path)
    || /^svg\//.test(path)
  ));

if (forbidden.length > 0) {
  console.error('npm package contains generated/unwanted files:');
  for (const path of forbidden.slice(0, 100)) console.error(`- ${path}`);
  if (forbidden.length > 100) console.error(`- ...and ${forbidden.length - 100} more`);
  process.exit(1);
}

const packageInfo = payload[0] ?? {};
console.log(`npm package contents passed: ${packageInfo.name ?? '<unknown>'}@${packageInfo.version ?? '<unknown>'}, ${files.length} files.`);
