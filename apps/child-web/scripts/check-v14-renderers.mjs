import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
const root = path.resolve(fileURLToPath(new URL("..", import.meta.url)));
const read = rel => fs.readFileSync(path.join(root, rel), "utf8");
const assert = (ok, msg) => { if (!ok) throw new Error(`V1.4 renderer check failed: ${msg}`); };
const registry = read("src/features/task-renderer/rendererRegistry.ts");
const router = read("src/features/task-renderer/TaskRenderer.tsx");
const library = read("src/components/renderers/V2RendererLibrary.tsx");
const ids = [
  "object-counter","bar-model","number-line","number-input","choice-grid","place-value","ten-frame",
  "column-arithmetic","array-board","grouping-board","formula-board","estimation-canvas","shape-gallery",
  "shape-canvas","sorting-board","direction-grid","ruler","clock","timeline","money-board","data-table",
  "pictograph","pattern-board"
];
const implementedLegacy = ["object-counter","bar-model","number-line","number-input"];
const implementedV2 = ids.filter(id => !implementedLegacy.includes(id) && id !== "column-arithmetic");
for (const id of ids) assert(registry.includes(`"${id}"`), `registry missing ${id}`);
for (const id of implementedV2) assert(registry.includes(`"${id}": implementedV2`), `${id} is not implementedV2`);
for (const id of implementedV2) assert(router.includes(`rendererId === "${id}"`), `${id} not routed by TaskRenderer`);
for (const id of implementedV2) assert(library.includes(`export function ${id.replace(/(^|-)(.)/g, (_,__,c)=>c.toUpperCase())}`) || library.includes(`export function ${({"choice-grid":"ChoiceGrid","place-value":"PlaceValue","ten-frame":"TenFrame","column-arithmetic":"ColumnArithmetic"}[id] ?? id)}`), `${id} component missing`);
assert(fs.existsSync(path.join(root, "src/components/renderers/ColumnArithmetic.tsx")), "B5 renderer missing");
assert(fs.existsSync(path.join(root, "src/lib/api/v2AttemptAdapter.ts")), "V2 attempt adapter missing");
assert(!/math-lab/.test(read("src/config.ts")), "legacy math-lab skin name remains");
console.log(`V1.4 renderer library check: PASS (${ids.length}/23 protocols; ${implementedV2.length} V2 renderers + 4 reused renderers)`);
