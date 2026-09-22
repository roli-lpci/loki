import { readFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const repoRoot = fileURLToPath(
  new URL('../', import.meta.url),
);

const packageJsonPath = fileURLToPath(
  new URL('../package.json', import.meta.url),
);

const expectedPackage = JSON.parse(
  readFileSync(
    packageJsonPath,
    'utf8',
  ),
);

if (
  typeof expectedPackage.name !== 'string'
  || expectedPackage.name.length === 0
) {
  console.error(
    'package.json does not contain a valid package name.',
  );

  process.exit(1);
}

if (
  typeof expectedPackage.version !== 'string'
  || expectedPackage.version.length === 0
) {
  console.error(
    'package.json does not contain a valid package version.',
  );

  process.exit(1);
}

const result = spawnSync(
  process.platform === 'win32'
    ? 'npm.cmd'
    : 'npm',
  [
    'pack',
    '--dry-run',
    '--json',
    '--ignore-scripts',
  ],
  {
    cwd: repoRoot,
    encoding: 'utf8',
    env: {
      ...process.env,
      npm_config_loglevel: 'silent',
    },
  },
);

if (result.status !== 0) {
  process.stderr.write(
    result.stderr
    || result.stdout
    || 'npm pack --dry-run failed\n',
  );

  process.exit(
    result.status ?? 1,
  );
}

let payload;

try {
  payload = JSON.parse(
    result.stdout.trim(),
  );
} catch (error) {
  console.error(
    'Could not parse npm pack --dry-run --json output.',
  );

  console.error(
    result.stdout,
  );

  throw error;
}

let entries;

if (Array.isArray(payload)) {
  entries = payload;
} else if (
  payload
  && typeof payload === 'object'
  && Array.isArray(payload.files)
) {
  entries = [payload];
} else if (
  payload
  && typeof payload === 'object'
) {
  entries = Object.values(payload);
} else {
  entries = [];
}

const packageInfo = entries.find(
  entry => (
    entry
    && typeof entry === 'object'
    && Array.isArray(entry.files)
  ),
);

if (!packageInfo) {
  console.error(
    'npm pack did not return package metadata.',
  );

  console.error(
    JSON.stringify(
      payload,
      null,
      2,
    ),
  );

  process.exit(1);
}

const packageName = packageInfo.name;
const packageVersion = packageInfo.version;
const files = packageInfo.files;

if (
  typeof packageName !== 'string'
  || packageName.length === 0
  || packageName === '<unknown>'
) {
  console.error(
    'npm pack did not report a valid package name.',
  );

  process.exit(1);
}

if (
  typeof packageVersion !== 'string'
  || packageVersion.length === 0
  || packageVersion === '<unknown>'
) {
  console.error(
    'npm pack did not report a valid package version.',
  );

  process.exit(1);
}

if (packageName !== expectedPackage.name) {
  console.error(
    `npm package name mismatch: expected ${expectedPackage.name}, got ${packageName}`,
  );

  process.exit(1);
}

if (packageVersion !== expectedPackage.version) {
  console.error(
    `npm package version mismatch: expected ${expectedPackage.version}, got ${packageVersion}`,
  );

  process.exit(1);
}

if (files.length === 0) {
  console.error(
    'npm package contains zero detected files.',
  );

  process.exit(1);
}

const forbidden = files
  .map(
    file => file.path,
  )
  .filter(
    path => (
      /(^|\/)__pycache__\//.test(path)
      || /\.py[co]$/.test(path)
      || /(^|\/)[^/]+\.egg-info\//.test(path)
      || /^MagicMock\//.test(path)
      || /^svg\//.test(path)
      || /(^|\/)\.pytest_cache\//.test(path)
      || /(^|\/)\.DS_Store$/.test(path)
    ),
  );

if (forbidden.length > 0) {
  console.error(
    'npm package contains generated/unwanted files:',
  );

  for (
    const path
    of forbidden.slice(
      0,
      100,
    )
  ) {
    console.error(
      `- ${path}`,
    );
  }

  if (forbidden.length > 100) {
    console.error(
      `- ...and ${forbidden.length - 100} more`,
    );
  }

  process.exit(1);
}

console.log(
  `npm package contents passed: ${packageName}@${packageVersion}, ${files.length} files.`,
);
