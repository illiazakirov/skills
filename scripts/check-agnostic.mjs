#!/usr/bin/env node
// Fails when anything under skills/ depends on one harness: its variables, its tool names,
// its agent types or its slash syntax. The rules are .agents/agnostic.md.

import { readFileSync, readdirSync } from "node:fs";
import { extname, join, relative } from "node:path";

const root = new URL("..", import.meta.url).pathname;
const TEXT = new Set([".md", ".py", ".html", ".yaml", ".yml", ".json", ".css", ".js", ".mjs", ".sh", ".txt", ".env", ""]);
const FORBIDDEN = [
  ["CLAUDE_PLUGIN_ROOT", /CLAUDE_PLUGIN_ROOT/],
  ["allowed-tools frontmatter", /^allowed-tools:/],
  ["harness slash syntax /<plugin>:<skill>", /\/brand:/],
  ["plugin agent type", /brand:critic/],
  ["harness tool name", /\b(AskUserQuestion|TodoWrite|WebFetch|WebSearch)\b/],
  ["MCP tool name", /\bmcp__/],
  ["harness tool name", /\b(Task|Agent|Skill) tool\b/],
];

function* files(dir) {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    if (entry.name === "node_modules" || entry.name === "__pycache__") continue;
    const path = join(dir, entry.name);
    if (entry.isDirectory()) yield* files(path);
    else if (TEXT.has(extname(entry.name))) yield path;
  }
}

const hits = [];
for (const file of files(join(root, "skills"))) {
  readFileSync(file, "utf8").split("\n").forEach((line, i) => {
    for (const [label, pattern] of FORBIDDEN) {
      if (pattern.test(line)) hits.push(`${relative(root, file)}:${i + 1}: ${label}`);
    }
  });
}

if (hits.length) {
  console.error(hits.join("\n"));
  console.error(`\n${hits.length} harness-specific line(s) under skills/. See .agents/agnostic.md.`);
  process.exit(1);
}
console.log("No harness-specific text under skills/.");
