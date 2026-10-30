/** Cross-platform, dependency-preserving child UI launcher. No seed or DB operations. */
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

export function parseOptions(args) {
  const options = { skin: "exploration-lab", api: "http", port: "3100", ui: "v6", mode: "dev", dryRun: false, apiBase: undefined };
  const values = new Map([["--skin", "skin"], ["--api", "api"], ["--port", "port"], ["--api-base", "apiBase"]]);
  let modeSelected = false;
  for (let i = 0; i < args.length; i += 1) {
    const arg = args[i];
    if (values.has(arg)) {
      if (!args[i + 1] || args[i + 1].startsWith("--")) throw new Error(`${arg} requires a value`);
      options[values.get(arg)] = args[++i];
    } else if (arg === "--legacy") options.ui = "legacy";
    else if (arg === "--build" || arg === "--start") {
      if (modeSelected) throw new Error("Choose only one of --build and --start");
      options.mode = arg.slice(2); modeSelected = true;
    } else if (arg === "--dry-run") options.dryRun = true;
    else if (arg === "--help") return { help: true };
    else throw new Error(`Unknown argument: ${arg}`);
  }
  if (!["exploration-lab", "healing"].includes(options.skin)) throw new Error("--skin must be exploration-lab or healing");
  if (!["http", "mock"].includes(options.api)) throw new Error("--api must be http or mock");
  if (!/^\d+$/.test(options.port) || +options.port < 1024 || +options.port > 65535) throw new Error("--port must be 1024..65535");
  if (options.apiBase) {
    const url = new URL(options.apiBase);
    if (!["http:", "https:"].includes(url.protocol) || url.username || url.password) throw new Error("--api-base requires an HTTP(S) URL without credentials");
  }
  return options;
}

export function launchPlan(options, sourceEnv = process.env) {
  const env = { ...sourceEnv, NEXT_PUBLIC_CHILD_UI_VERSION: options.ui, NEXT_PUBLIC_CHILD_MATH_SKIN: options.skin, NEXT_PUBLIC_LEARNING_API_MODE: options.api,
    NEXT_DIST_DIR: `.next-${options.ui}-${options.skin === "healing" ? "healing" : "lab"}` };
  if (options.apiBase) env.NEXT_PUBLIC_LEARNING_API_BASE_URL = options.apiBase;
  const args = ["--workspace", "@learning/child-web", "run", options.mode];
  if (options.mode !== "build") args.push("--", "--port", options.port, "--hostname", "127.0.0.1");
  return { env, args };
}

function main() {
  const options = parseOptions(process.argv.slice(2));
  if (options.help) {
    console.log("node scripts/run-child-ui.mjs [--skin exploration-lab|healing] [--api http|mock] [--port 3100] [--api-base http://localhost:8000] [--legacy] [--build|--start] [--dry-run]");
    return;
  }
  if (+process.versions.node.split(".")[0] < 22) throw new Error("Node.js 22 or later is required by this repository");
  const { env, args } = launchPlan(options);
  console.log(`Child UI: ${options.ui} | skin: ${options.skin} | API: ${options.api} | ${options.mode} | ${env.NEXT_DIST_DIR}`);
  if (options.api === "mock") console.log("PREVIEW ONLY: built-in mock data, not live learning records.");
  if (options.dryRun) { console.log(JSON.stringify({ args, ui: env.NEXT_PUBLIC_CHILD_UI_VERSION, skin: env.NEXT_PUBLIC_CHILD_MATH_SKIN, api: env.NEXT_PUBLIC_LEARNING_API_MODE, distDir: env.NEXT_DIST_DIR }, null, 2)); return; }
  const npmCli = process.env.npm_execpath;
  const executable = npmCli ? process.execPath : (process.platform === "win32" ? "npm.cmd" : "npm");
  const child = spawn(executable, npmCli ? [npmCli, ...args] : args, {
    cwd: path.resolve(path.dirname(fileURLToPath(import.meta.url)), ".."), env, stdio: "inherit",
    shell: !npmCli && process.platform === "win32"
  });
  for (const signal of ["SIGINT", "SIGTERM"]) process.once(signal, () => child.kill(signal));
  child.once("error", error => { console.error(`Launch failed: ${error.message}. Run npm ci from the repository root first.`); process.exitCode = 1; });
  child.once("exit", (code, signal) => { process.exitCode = code ?? (signal === "SIGINT" ? 130 : 1); });
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try { main(); } catch (error) { console.error(error instanceof Error ? error.message : String(error)); process.exitCode = 1; }
}
