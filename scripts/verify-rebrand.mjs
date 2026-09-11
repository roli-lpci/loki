import { readdir, readFile, stat } from 'node:fs/promises';
import { join, relative } from 'node:path';

const root = new URL('../', import.meta.url).pathname;
const forbidden = [/\bHermes\b/i, /Nous\s*Research/i, /NousResearch/i, /nous-research/i, /BuilderStudio/i, /\bAurelius\b/i, /aurelius-agent/i, /aureliusagent\.dev/i, /@wundercorp\/aurelius/i, /\baure\b/i];
const ignoredDirectories = new Set([
  '.git',
  '.venv',
  'venv',
  '.tox',
  '.pytest_cache',
  '.mypy_cache',
  '.ruff_cache',
  '__pycache__',
  'node_modules',
  'dist',
  'build',
  'coverage',
  '.terraform',
  '.next',
  '.cache',
]);
const ignoredFiles = new Set([
  '.coverage',
  '.DS_Store',
  '.env',
  '.env.local',
  '.env.development.local',
  '.env.test.local',
  '.env.production.local',
  'terraform.tfstate',
  'terraform.tfstate.backup',
]);
const allowed = new Set(['THIRD_PARTY_NOTICES.md', 'scripts/verify-rebrand.mjs']);
const failures = [];

async function walk(directory) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    if (entry.isDirectory() && ignoredDirectories.has(entry.name)) continue;
    if (entry.isFile() && ignoredFiles.has(entry.name)) continue;
    const full = join(directory, entry.name);
    const rel = relative(root, full);
    if (allowed.has(rel)) continue;
    if (forbidden.some((pattern) => pattern.test(entry.name))) failures.push(`path: ${rel}`);
    if (entry.isDirectory()) {
      await walk(full);
      continue;
    }
    const info = await stat(full);
    if (info.size > 8 * 1024 * 1024) continue;
    let buffer;
    try { buffer = await readFile(full); } catch { continue; }
    if (buffer.includes(0)) continue;
    const text = buffer.toString('utf8');
    if (forbidden.some((pattern) => pattern.test(text))) failures.push(`content: ${rel}`);
  }
}

await walk(root);
if (failures.length) {
  console.error('Legacy branding found:\n' + failures.slice(0, 100).join('\n'));
  process.exit(1);
}
console.log('Brand verification passed: Loki Agent / WunderCorp, Inc.');
