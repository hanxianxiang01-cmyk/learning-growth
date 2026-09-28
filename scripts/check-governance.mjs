import fs from "node:fs";
import path from "node:path";

const required = [
  "README.md",
  "PROJECT_STATUS.md",
  "ROADMAP.md",
  "CHANGELOG.md",
  "AI_CONTRIBUTING.md",
  "CONTRIBUTING.md",
  "VERSION",
  "GOVERNANCE_VERSION",
  "docs/governance/WORKFLOW.md",
  "docs/governance/VERSIONING.md",
  "docs/governance/CONTRACT_DRIFT_REGISTER.md",
  "docs/adr/ADR-0006-git-is-working-source-of-truth.md",
  ".github/pull_request_template.md",
  ".github/workflows/ci.yml"
];

const errors = required
  .filter(rel => !fs.existsSync(path.join(process.cwd(), rel)))
  .map(rel => `missing ${rel}`);

const changelog = fs.readFileSync("CHANGELOG.md", "utf8");
if (!changelog.includes("# [Unreleased]")) {
  errors.push("CHANGELOG must contain [Unreleased]");
}

if (errors.length) {
  console.error("Governance check FAILED");
  errors.forEach(e => console.error(`- ${e}`));
  process.exit(1);
}

console.log("Governance check OK");
