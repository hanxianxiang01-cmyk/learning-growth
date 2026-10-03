import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const ts = require("typescript");
const root = path.resolve(fileURLToPath(new URL("..", import.meta.url)));
const sourcePath = path.join(root, "src/features/task-renderer/columnArithmetic.ts");

const source = fs.readFileSync(sourcePath, "utf8");
const compiled = ts.transpileModule(source, {
  compilerOptions: {
    target: ts.ScriptTarget.ES2022,
    module: ts.ModuleKind.CommonJS,
    strict: true
  },
  reportDiagnostics: true
});

const syntaxErrors = (compiled.diagnostics ?? []).filter(
  diagnostic => diagnostic.category === ts.DiagnosticCategory.Error
);
if (syntaxErrors.length) {
  throw new Error(
    syntaxErrors.map(item => ts.flattenDiagnosticMessageText(item.messageText, "\n")).join("\n")
  );
}

const module = { exports: {} };
const runner = new Function("require", "module", "exports", compiled.outputText);
runner(require, module, module.exports);

const {
  initialColumnArithmeticState,
  setResultDigit,
  toggleCarry,
  evaluateColumnArithmetic
} = module.exports;

const config = {
  operands: [47, 28],
  places: ["ones", "tens", "hundreds"],
  operand_layout: "fixed"
};

let state = initialColumnArithmeticState(config);
state = setResultDigit(state, "ones", 5);
state = setResultDigit(state, "tens", 7);
state = setResultDigit(state, "hundreds", 0);
state = toggleCarry(state, "ones");

const pass = evaluateColumnArithmetic(config, state);
if (pass.status !== "PASS" || pass.answer !== 75) {
  throw new Error(`PASS case failed: ${JSON.stringify(pass)}`);
}

const fail = evaluateColumnArithmetic(
  config,
  setResultDigit(state, "tens", 8)
);
if (fail.status !== "FAIL") {
  throw new Error(`FAIL case failed: ${JSON.stringify(fail)}`);
}

const partial = evaluateColumnArithmetic(
  config,
  setResultDigit(initialColumnArithmeticState(config), "ones", 5)
);
if (partial.status !== "PARTIAL") {
  throw new Error(`PARTIAL case failed: ${JSON.stringify(partial)}`);
}

const invalid = evaluateColumnArithmetic(
  config,
  setResultDigit(initialColumnArithmeticState(config), "ones", 10)
);
if (invalid.status !== "INVALID") {
  throw new Error(`INVALID case failed: ${JSON.stringify(invalid)}`);
}

console.log("FE-1403 B5 evaluator check: PASS");
