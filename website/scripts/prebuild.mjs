#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import { mkdirSync, writeFileSync, existsSync, statSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const websiteDir = resolve(scriptDir, "..");
const repoRoot = resolve(websiteDir, "..");
const extractScript = join(scriptDir, "extract-skills.py");
const llmsScript = join(scriptDir, "generate-llms-txt.py");
const cronBlueprintsScript = join(scriptDir, "extract-automation-blueprints.py");
const pluginsScript = join(scriptDir, "extract-plugins.py");
const outputFile = join(websiteDir, "static", "api", "skills.json");
const pluginsOutputFile = join(websiteDir, "static", "api", "plugins.json");
const pluginsMetaOutputFile = join(websiteDir, "static", "api", "plugins-meta.json");
const unifiedIndexFile = join(websiteDir, "static", "api", "skills-index.json");
const unifiedIndexUrl = "https://loki.computer/api/skills-index.json";
const unifiedIndexMaxAgeMs = 24 * 60 * 60 * 1000;

function commandExists(command, args = ["--version"]) {
  const result = spawnSync(command, args, { stdio: "ignore", cwd: repoRoot });
  return !result.error && result.status === 0;
}

function pythonCandidates() {
  const candidates = [];
  const unixVenvPython = join(repoRoot, ".venv", "bin", "python");
  const windowsVenvPython = join(repoRoot, ".venv", "Scripts", "python.exe");
  if (existsSync(unixVenvPython)) {
    candidates.push({ command: unixVenvPython, prefix: [] });
  }
  if (existsSync(windowsVenvPython)) {
    candidates.push({ command: windowsVenvPython, prefix: [] });
  }
  if (commandExists("uv")) {
    candidates.push({ command: "uv", prefix: ["run", "--no-project", "--with", "pyyaml==6.0.3", "python"] });
  }
  candidates.push({ command: "python3", prefix: [] });
  candidates.push({ command: "python", prefix: [] });
  return candidates;
}

function resolvePython() {
  for (const candidate of pythonCandidates()) {
    const result = spawnSync(
      candidate.command,
      [...candidate.prefix, "-c", "import yaml"],
      { stdio: "ignore", cwd: repoRoot },
    );
    if (!result.error && result.status === 0) {
      return candidate;
    }
  }
  return null;
}

const python = resolvePython();

function writeEmptyFallback(reason) {
  mkdirSync(dirname(outputFile), { recursive: true });
  writeFileSync(outputFile, "[]\n");
  console.warn(`[prebuild] ${reason}; wrote empty skills.json fallback`);
}

function runPython(script, label) {
  if (!existsSync(script)) {
    console.warn(`[prebuild] ${label} skipped: script missing`);
    return false;
  }
  if (!python) {
    console.warn(`[prebuild] ${label} skipped: no Python environment with PyYAML is available`);
    return false;
  }
  const result = spawnSync(
    python.command,
    [...python.prefix, script],
    { stdio: "inherit", cwd: websiteDir },
  );
  if (result.error || result.status !== 0) {
    console.warn(`[prebuild] ${label} exited with status ${result.status ?? "unknown"}`);
    return false;
  }
  return true;
}

async function ensureUnifiedIndex() {
  if (existsSync(unifiedIndexFile)) {
    try {
      const age = Date.now() - statSync(unifiedIndexFile).mtimeMs;
      if (age < unifiedIndexMaxAgeMs) {
        return true;
      }
    } catch {
    }
  }

  try {
    const response = await fetch(unifiedIndexUrl, { headers: { accept: "application/json" } });
    if (!response.ok) {
      return existsSync(unifiedIndexFile);
    }
    const text = await response.text();
    const parsed = JSON.parse(text);
    if (!parsed || !Array.isArray(parsed.skills)) {
      return existsSync(unifiedIndexFile);
    }
    mkdirSync(dirname(unifiedIndexFile), { recursive: true });
    writeFileSync(unifiedIndexFile, text);
    console.log(`[prebuild] refreshed skills-index.json from ${unifiedIndexUrl}`);
    return true;
  } catch (error) {
    console.warn(`[prebuild] skills-index.json refresh skipped: ${error}`);
    return existsSync(unifiedIndexFile);
  }
}

await ensureUnifiedIndex();

if (!runPython(extractScript, "extract-skills.py")) {
  writeEmptyFallback("extract-skills.py unavailable");
}

runPython(llmsScript, "generate-llms-txt.py");
runPython(cronBlueprintsScript, "extract-automation-blueprints.py");

if (!runPython(pluginsScript, "extract-plugins.py")) {
  mkdirSync(dirname(pluginsOutputFile), { recursive: true });
  writeFileSync(pluginsOutputFile, "[]\n");
  writeFileSync(
    pluginsMetaOutputFile,
    `${JSON.stringify({ generatedAt: new Date().toISOString(), total: 0, byTier: { official: 0, community: 0 }, removedCount: 0 })}\n`,
  );
  console.warn("[prebuild] wrote empty plugin catalog fallback");
}
