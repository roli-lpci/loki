import { readFile, readdir } from 'node:fs/promises'
import path from 'node:path'
import process from 'node:process'
import { fileURLToPath } from 'node:url'

const repositoryRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const workspacePaths = [
  'apps/desktop',
  'apps/bootstrap-installer',
  'tui-ui',
  'web'
]
const sourceExtensions = new Set(['.cjs', '.css', '.html', '.js', '.jsx', '.mjs', '.ts', '.tsx'])
const ignoredDirectories = new Set(['.git', 'build', 'coverage', 'dist', 'node_modules', 'out', 'target'])

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

async function collectWorkspaceFiles(workspaceRoot) {
  const files = new Set()

  async function walk(directory) {
    for (const entry of await readdir(directory, { withFileTypes: true })) {
      if (entry.isDirectory() && ignoredDirectories.has(entry.name)) {
        continue
      }
      const absolutePath = path.join(directory, entry.name)
      if (entry.isDirectory()) {
        await walk(absolutePath)
        continue
      }
      if (entry.isFile() && sourceExtensions.has(path.extname(entry.name))) {
        files.add(absolutePath)
      }
    }
  }

  await walk(workspaceRoot)

  const pendingCssFiles = [...files].filter((filename) => path.extname(filename) === '.css')
  while (pendingCssFiles.length > 0) {
    const filename = pendingCssFiles.pop()
    const source = await readFile(filename, 'utf8')
    for (const match of source.matchAll(/@import\s+['"](\.{1,2}\/[^'"]+)['"]/g)) {
      const importedPath = path.resolve(path.dirname(filename), match[1])
      if (path.extname(importedPath) !== '.css' || files.has(importedPath)) {
        continue
      }
      files.add(importedPath)
      pendingCssFiles.push(importedPath)
    }
  }

  return files
}

function dependencyIsReferenced(dependencyName, sources) {
  const escapedName = escapeRegExp(dependencyName)
  const patterns = [
    new RegExp(`(?:from\\s*|import\\s*(?:type\\s*)?|require\\(\\s*|import\\(\\s*)['"]${escapedName}(?:/[^'"]*)?['"]`),
    new RegExp(`@(?:import|plugin|source)\\s+['"]${escapedName}(?:/[^'"]*)?['"]`),
    new RegExp(`node_modules[\\\\/]${escapedName}(?:[\\\\/]|['"])`)
  ]
  return sources.some((source) => patterns.some((pattern) => pattern.test(source)))
}

const failures = []

for (const workspacePath of workspacePaths) {
  const workspaceRoot = path.join(repositoryRoot, workspacePath)
  const packageJson = JSON.parse(await readFile(path.join(workspaceRoot, 'package.json'), 'utf8'))
  const dependencies = Object.keys(packageJson.dependencies ?? {})
  const files = await collectWorkspaceFiles(workspaceRoot)
  const sources = await Promise.all([...files].map((filename) => readFile(filename, 'utf8')))

  for (const dependencyName of dependencies) {
    if (!dependencyIsReferenced(dependencyName, sources)) {
      failures.push(`${workspacePath}: ${dependencyName}`)
    }
  }
}

if (failures.length > 0) {
  console.error('Unused direct workspace dependencies detected:')
  for (const failure of failures) {
    console.error(`  - ${failure}`)
  }
  console.error('Remove stale dependencies or make their direct usage explicit.')
  process.exit(1)
}

console.log('Workspace runtime dependency references look clean.')
