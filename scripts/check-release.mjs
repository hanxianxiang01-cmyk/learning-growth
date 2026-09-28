import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const read = rel => fs.readFileSync(path.join(root, rel), "utf8");
const readJson = rel => JSON.parse(read(rel));

const version = read("VERSION").trim();
const rootPkg = readJson("package.json");
const childPkg = readJson("apps/child-web/package.json");
const project = readJson("project_manifest.json");
const releaseIndex = readJson("releases/index.json");
const releasePath = `releases/${version}.json`;

const errors = [];

for (const [name, value] of [
  ["package.json", rootPkg.version],
  ["apps/child-web/package.json", childPkg.version],
  ["project_manifest.json", project.version],
  ["releases/index.json current", releaseIndex.current]
]) {
  if (value !== version) errors.push(`${name}: ${value} != ${version}`);
}

if (!fs.existsSync(path.join(root, releasePath))) {
  errors.push(`missing ${releasePath}`);
} else {
  const release = readJson(releasePath);
  if (release.version !== version) {
    errors.push(`${releasePath}: ${release.version} != ${version}`);
  }
}

const changelog = read("CHANGELOG.md");
if (!changelog.includes(`# [${version}]`)) {
  errors.push(`CHANGELOG missing # [${version}]`);
}

if (errors.length) {
  console.error("Release check FAILED");
  errors.forEach(e => console.error(`- ${e}`));
  process.exit(1);
}
console.log(`Release check OK: ${version}`);
