import { execSync } from "node:child_process";

// 分支命名强制校验（配合 docs/governance/BRANCH_AND_PR_POLICY.md）
// 输入优先级：GITHUB_HEAD_REF（PR 源分支）> GITHUB_REF_NAME（push）> git 当前分支
// 允许通过环境变量 SKIP_BRANCH_CHECK=1 跳过（仅本地调试用，CI 不设）

const ALLOWED = [
  { re: /^main$/, label: "main" },
  { re: /^fix\/BUG-\d+(-[a-z0-9-]+)?$/, label: "fix/BUG-xxxx-*" },
  { re: /^hotfix\/BUG-\d+(-[a-z0-9-]+)?$/, label: "hotfix/BUG-xxxx-*" },
  { re: /^feat\/FE-13\d{2}(-[a-z0-9-]+)?$/, label: "feat/FE-13xx-*" },
  { re: /^docs\/[a-z0-9-]+$/, label: "docs/*" },
  { re: /^chore\/[a-z0-9-]+$/, label: "chore/*" },
  { re: /^dependabot\//, label: "dependabot/*" },
  { re: /^renovate\//, label: "renovate/*" },
];

function currentBranch() {
  if (process.env.GITHUB_HEAD_REF) return process.env.GITHUB_HEAD_REF;
  if (process.env.GITHUB_REF_NAME) return process.env.GITHUB_REF_NAME;
  try {
    return execSync("git rev-parse --abbrev-ref HEAD", {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
    }).trim();
  } catch {
    return "";
  }
}

const branch = currentBranch();

if (process.env.SKIP_BRANCH_CHECK === "1") {
  console.log(`Branch check skipped (branch=${branch || "n/a"})`);
  process.exit(0);
}

if (!branch) {
  console.error("Branch check FAILED: cannot determine current branch name.");
  process.exit(1);
}

const ok = ALLOWED.some(({ re }) => re.test(branch));

if (!ok) {
  console.error(`Branch check FAILED: branch name "${branch}" is not allowed.`);
  console.error("Allowed patterns:");
  ALLOWED.forEach(({ label }) => console.error(`  - ${label}`));
  process.exit(1);
}

console.log(`Branch check OK (${branch})`);