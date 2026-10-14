import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";
const root = process.env.V6_SOURCE_ROOT || path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const app = path.join(root, "apps/child-web");
const base = process.env.V6_ARTIFACT_DIR || path.join(root, ".cache/v6-isolated");
const out = path.join(base, "harness");
const require = createRequire(path.join(app, "package.json"));
try {
  const ts = require(process.env.V6_TYPESCRIPT_PATH || "typescript");
  fs.mkdirSync(out, { recursive: true });
  fs.mkdirSync(path.join(base, "evidence"), { recursive: true });
  const modules = {}, diagnostics = [];
  const walk = directory => {
    for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
      const filename = path.join(directory, entry.name);
      if (entry.isDirectory()) { walk(filename); continue; }
      if (!/\.(ts|tsx|json)$/.test(entry.name) || entry.name.endsWith(".d.ts")) continue;
      const id = path.relative(app, filename).split(path.sep).join("/");
      if (entry.name.endsWith(".json")) { modules[id] = "module.exports=" + fs.readFileSync(filename, "utf8"); continue; }
      const result = ts.transpileModule(fs.readFileSync(filename, "utf8"), {
        compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true, resolveJsonModule: true },
        reportDiagnostics: true, fileName: filename
      });
      for (const diagnostic of result.diagnostics || []) diagnostics.push({ file: id, text: ts.flattenDiagnosticMessageText(diagnostic.messageText, "\n") });
      modules[id] = result.outputText;
    }
  };
  walk(path.join(app, "src"));
  let vendor, vendorSource;
  if (process.env.V6_VENDOR_BOOTSTRAP) {
    // Optional diagnostic runtime: file must expose window.__vendor.{r,e,j}.
    // The actual runtime version is captured by every browser test, never relabeled React 18.
    vendor = fs.readFileSync(process.env.V6_VENDOR_BOOTSTRAP, "utf8");
    vendorSource = "explicit external diagnostic runtime";
  } else {
    const reactDir = path.dirname(require.resolve("react/package.json"));
    const domDir = path.dirname(require.resolve("react-dom/package.json"));
    vendor = fs.readFileSync(path.join(reactDir, "umd/react.development.js"), "utf8") + "\n" +
      fs.readFileSync(path.join(domDir, "umd/react-dom.development.js"), "utf8") + `
      window.__vendor = {r:window.React, e:window.ReactDOM, j:{Fragment:window.React.Fragment,
        jsx:(type,props,key)=>window.React.createElement(type,key===undefined?props:{...props,key}),
        jsxs:(type,props,key)=>window.React.createElement(type,key===undefined?props:{...props,key})}};`;
    vendorSource = "installed locked React/ReactDOM UMD dependencies";
  }
  fs.writeFileSync(path.join(out, "vendor-inline.js"), vendor);
  fs.writeFileSync(path.join(out, "modules.json"), JSON.stringify(modules));
  const report = { compiler: ts.version, compilerSource: process.env.V6_TYPESCRIPT_PATH ? "external diagnostic compiler" : "installed dependency", vendorSource,
    scope: "Syntax transpilation only; NOT full app typecheck", modules: Object.keys(modules).length, diagnostics };
  fs.writeFileSync(path.join(base, "evidence/transpile.json"), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
  process.exitCode = diagnostics.length ? 1 : 0;
} catch (error) {
  console.error("BLOCKED: isolated harness preparation failed. Install the repository's locked dependencies with npm ci first.");
  console.error(error instanceof Error ? error.message : String(error));
  process.exitCode = 2;
}
