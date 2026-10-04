// 数据卫生静态扫描（docs/governance/QA_DATA_HYGIENE.md R1/R2）。
// 扫描范围：会写真实后端的代码目录。违例即 FAIL。
import fs from "node:fs";
import path from "node:path";

const REAL_CHILD = "00000000-0000-0000-0000-000000000001";
const QA_CHILD = "00000000-0000-0000-0000-000000000099";

// 会向真实后端写入测试流量的目录——禁止引用真实 child
// （产品 seed 在 apps/learning-api/scripts，不在此范围；那是合法演示身份引用）
const CHILD_SCAN = ["scripts", "apps/child-web/e2e"];
// 全仓扫描（凭据类）——这些目录外的所有源码文件
const CRED_SCAN_DIRS = ["scripts", "apps/learning-api/app", "apps/learning-api/scripts",
  "apps/learning-api/tests", "apps/child-web/e2e", "apps/child-web/src", "packages"];
const CRED_EXT = /\.(py|mjs|ts|mts|tsx|sh|json|yaml|yml)$/;
const CRED_ALLOW = [ // 白名单：占位符示例
  "apps/learning-api/.env.example",
];

const errors = [];

function walk(dir, out = []) {
  if (!fs.existsSync(dir)) return out;
  const st = fs.statSync(dir);
  if (st.isFile()) { out.push(dir); return out; }
  for (const e of fs.readdirSync(dir)) {
    if (e === "node_modules" || e.startsWith(".")) continue;
    walk(path.join(dir, e), out);
  }
  return out;
}

// R1：测试流量目录禁止出现真实 child 字面量
for (const target of CHILD_SCAN) {
  for (const f of walk(target)) {
    const src = fs.readFileSync(f, "utf8");
    if (src.includes(REAL_CHILD) && !src.includes(QA_CHILD)) {
      errors.push(`R1 violation: ${f} 写真实后端却引用真实 child …0001（应使用 QA child …0099）`);
    }
  }
}

// R2：凭据字面量
const HOST = "pg.rds.aliyuncs.com";
const URLPW = /postgres(?:ql)?(?:\+[a-z]+)?:\/\/[^/\s"']*:[^/\s"']+@/;
const files = [];
for (const d of CRED_SCAN_DIRS) walk(d, files);
for (const f of files) {
  if (!CRED_EXT.test(f)) continue;
  if (f.endsWith("check-data-hygiene.mjs")) continue; // 扫描器自身含检测模式常量
  if (CRED_ALLOW.some(a => f.endsWith(a))) continue;
  const src = fs.readFileSync(f, "utf8");
  if (src.includes(HOST)) errors.push(`R2 violation: ${f} 含 RDS host 字面量`);
  const m = src.match(URLPW);
  if (m && !/user:CHANGE_ME/.test(m[0])) errors.push(`R2 violation: ${f} 含带密码连接串字面量`);
}

if (errors.length) {
  console.error("Data hygiene check FAILED");
  errors.forEach(e => console.error(`- ${e}`));
  process.exit(1);
}
console.log("Data hygiene check OK（R1 测试流量分池 / R2 无凭据字面量）");
