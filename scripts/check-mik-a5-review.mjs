#!/usr/bin/env node
/**
 * MIK-A5 / FE-1445 V6 ZIP integration REVIEW GATE.
 * Does not stand in for React18/Next14 build, real browser, HTTP/DB, or L3.
 * Fail fast. All paths are repo-root relative; no modification of task state.
 */
import { spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const localTsc=resolve(root,'node_modules/.bin/tsc');
const tsc=existsSync(localTsc)?localTsc:'tsc';
const gates=[
 ['MIK-A5 scoped strict TypeScript',tsc,['-p','tsconfig.mik-a5-isolated.json']],
 ['MIK-A5 domain, renderer wiring and responsive Router contracts',process.execPath,['--test',
  'tests/a5-16/natural-intent.test.cjs','tests/a5-16/scene-16.test.cjs',
  'tests/a5-16/react-handler.test.cjs','tests/spikes/mik-a5-live/live-domain-and-wiring.test.cjs',
  'tests/spikes/mik-a5-live/router-width-contract.test.cjs']],
 ['SAFE-01 envelope audit',process.execPath,['tests/spikes/safe01-envelope-audit.cjs']],
 ['Task-pinned Router policy',process.execPath,['tests/spikes/implementation-policy.test.cjs']],
 ['V1.4 contract gate',process.execPath,['apps/child-web/scripts/check-v14-contracts.mjs']],
 ['V6 full migration inventory',process.execPath,['apps/child-web/scripts/check-v6-full.mjs']],
];
for(const [label,command,args] of gates){
 process.stdout.write(`\n== ${label} ==\n`);
 const r=spawnSync(command,args,{cwd:root,stdio:'inherit'});
 if(r.error||r.status!==0){
  console.error(`MIK A5 REVIEW FAILED: ${label}${r.error?`: ${r.error.message}`:''}`);
  process.exit(r.status??2);
 }
}
console.log('\nMIK-A5 REVIEW GATE PASS — Not real React/Next/Browser/HTTP-DB/L3 approval.');
