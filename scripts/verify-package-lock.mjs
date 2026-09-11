import { readFile, readdir, stat } from 'node:fs/promises';
import { join, relative } from 'node:path';

const root = new URL('../', import.meta.url);
const packageJson = JSON.parse(await readFile(new URL('package.json', root), 'utf8'));
const packageLock = JSON.parse(await readFile(new URL('package-lock.json', root), 'utf8'));
const lockedRoot = packageLock.packages?.[''];

const failures = [];

if (!lockedRoot) failures.push('package-lock.json has no root package entry');
if (lockedRoot?.name !== packageJson.name) failures.push(`root name differs: ${lockedRoot?.name ?? '<missing>'} != ${packageJson.name}`);
if (lockedRoot?.version !== packageJson.version) failures.push(`root version differs: ${lockedRoot?.version ?? '<missing>'} != ${packageJson.version}`);

const declaredWorkspaces = [...(packageJson.workspaces ?? [])].sort();
const lockedWorkspaces = [...(lockedRoot?.workspaces ?? [])].sort();
if (JSON.stringify(declaredWorkspaces) !== JSON.stringify(lockedWorkspaces)) {
  failures.push(`workspace list differs:\n  package.json: ${declaredWorkspaces.join(', ')}\n  package-lock: ${lockedWorkspaces.join(', ')}`);
}

async function exists(path) {
  try {
    await stat(path);
    return true;
  } catch {
    return false;
  }
}

async function expandWorkspace(pattern) {
  const rootPath = decodeURIComponent(root.pathname);
  if (!pattern.includes('*')) return [pattern];
  if (!pattern.endsWith('/*') || pattern.slice(0, -2).includes('*')) return [];
  const parent = pattern.slice(0, -2);
  const parentPath = join(rootPath, parent);
  if (!(await exists(parentPath))) return [];
  const entries = await readdir(parentPath, { withFileTypes: true });
  return entries.filter(entry => entry.isDirectory()).map(entry => `${parent}/${entry.name}`);
}

const workspacePaths = [];
for (const pattern of packageJson.workspaces ?? []) {
  workspacePaths.push(...await expandWorkspace(pattern));
}

for (const workspacePath of workspacePaths) {
  const rootPath = decodeURIComponent(root.pathname);
  const manifestPath = join(rootPath, workspacePath, 'package.json');
  if (!(await exists(manifestPath))) continue;
  const workspaceManifest = JSON.parse(await readFile(manifestPath, 'utf8'));
  const lockedWorkspace = packageLock.packages?.[workspacePath];
  if (!lockedWorkspace) {
    failures.push(`workspace missing from lock: ${workspacePath}`);
    continue;
  }
  if (workspaceManifest.name && lockedWorkspace.name !== workspaceManifest.name) {
    failures.push(`workspace name differs at ${workspacePath}: ${lockedWorkspace.name ?? '<missing>'} != ${workspaceManifest.name}`);
  }
  if (workspaceManifest.version && lockedWorkspace.version !== workspaceManifest.version) {
    failures.push(`workspace version differs at ${workspacePath}: ${lockedWorkspace.version ?? '<missing>'} != ${workspaceManifest.version}`);
  }
  if (workspaceManifest.name) {
    const nodeModulesEntry = packageLock.packages?.[`node_modules/${workspaceManifest.name}`];
    if (!nodeModulesEntry?.link || nodeModulesEntry.resolved !== workspacePath) {
      failures.push(`workspace link missing/stale for ${workspaceManifest.name}: expected node_modules link -> ${workspacePath}`);
    }
  }
}

if (failures.length) {
  console.error('npm lockfile verification failed:\n' + failures.map(item => `- ${item}`).join('\n'));
  console.error('\nRun `npm install --package-lock-only --ignore-scripts` and commit the resulting package-lock.json.');
  process.exit(1);
}

console.log(`npm lockfile verification passed for ${packageJson.name}@${packageJson.version}.`);
