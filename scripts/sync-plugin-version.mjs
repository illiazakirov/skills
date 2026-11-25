#!/usr/bin/env node
// Copies each plugin's package.json version into the .claude-plugin/plugin.json beside it.
// A plugin is a bucket folder skills/<bucket>/ holding both files, and a workspace.
// Runs as part of `npm run version`, right after `changeset version`.
// With --check it changes nothing and exits 1 if any plugin's two versions differ.

import { existsSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const repo = join(dirname(fileURLToPath(import.meta.url)), "..");
const check = process.argv.includes("--check");

function* plugins() {
  const skills = join(repo, "skills");
  for (const bucket of readdirSync(skills, { withFileTypes: true })) {
    const dir = join(skills, bucket.name);
    if (bucket.isDirectory() && existsSync(join(dir, "package.json"))
        && existsSync(join(dir, ".claude-plugin", "plugin.json"))) yield dir;
  }
}

let drift = 0;
for (const dir of plugins()) {
  const where = relative(repo, dir);
  const { version } = JSON.parse(readFileSync(join(dir, "package.json"), "utf8"));
  const pluginPath = join(dir, ".claude-plugin", "plugin.json");
  const source = readFileSync(pluginPath, "utf8");
  const plugin = JSON.parse(source);
  if (plugin.version === version) {
    console.log(`${where}: ${version} (in sync)`);
    continue;
  }
  if (check) {
    console.error(`${where}: plugin.json is ${plugin.version}, package.json is ${version}. Run \`npm run version\`.`);
    drift++;
    continue;
  }
  // Rewrite only the version line, to keep the key order and the formatting.
  const updated = source.replace(/("version"\s*:\s*")[^"]*(")/, `$1${version}$2`);
  if (JSON.parse(updated).version !== version) {
    console.error(`${where}: no version field to replace in plugin.json.`);
    process.exit(1);
  }
  writeFileSync(pluginPath, updated);
  console.log(`${where}: plugin.json ${plugin.version} -> ${version}`);
}
process.exit(drift ? 1 : 0);
