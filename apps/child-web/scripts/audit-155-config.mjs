// FE-1432 实灌验证①：155 题包 config × 我方 15 专件 parser 兼容性审计
// （number-line/object-counter/number-input/column-arithmetic 走基座通用 config，无独立 parser）
import { readFileSync } from "node:fs";
import { parseBarModelConfig } from "../src/features/task-renderer/barModelV2.ts";
import { parsePlaceValueConfig } from "../src/features/task-renderer/placeValueV2.ts";
import { parseFormulaConfig } from "../src/features/task-renderer/formulaBoardV2.ts";
import { parseArrayBoardConfig } from "../src/features/task-renderer/arrayBoardV2.ts";
import { parseGroupingConfig } from "../src/features/task-renderer/groupingBoardV2.ts";
import { parseEstimationConfig } from "../src/features/task-renderer/estimationCanvasV2.ts";
import { parseShapeGalleryConfig } from "../src/features/task-renderer/shapeGalleryV2.ts";
import { parseShapeCanvasConfig } from "../src/features/task-renderer/shapeCanvasV2.ts";
import { parseSortingConfig } from "../src/features/task-renderer/sortingBoardV2.ts";
import { parseDirectionConfig } from "../src/features/task-renderer/directionGridV2.ts";
import { parseRulerConfig } from "../src/features/task-renderer/rulerV2.ts";
import { parseClockConfig } from "../src/features/task-renderer/clockV2.ts";
import { parseMoneyConfig } from "../src/features/task-renderer/moneyBoardV2.ts";
import { parsePatternConfig } from "../src/features/task-renderer/patternBoardV2.ts";
import { parseTenFrameConfig } from "../src/features/task-renderer/tenFrameV2.ts";

const d = JSON.parse(readFileSync(process.argv[2], "utf8"));
const qs = d.questions;
const parsers = {
  "bar-model": parseBarModelConfig, "place-value": parsePlaceValueConfig,
  "formula-board": parseFormulaConfig, "array-board": parseArrayBoardConfig,
  "grouping-board": parseGroupingConfig, "estimation-canvas": parseEstimationConfig,
  "shape-gallery": parseShapeGalleryConfig, "shape-canvas": parseShapeCanvasConfig,
  "sorting-board": parseSortingConfig, "direction-grid": parseDirectionConfig,
  "ruler": parseRulerConfig, "clock": parseClockConfig,
  "money-board": parseMoneyConfig, "pattern-board": parsePatternConfig,
  "ten-frame": parseTenFrameConfig,
};
const ok = [], fail = [], noParser = [];
for (const q of qs) {
  const r = q.renderer_id;
  const cfg = q.task_ui_schema.workspaces[0].config;
  const fn = parsers[r];
  if (!fn) { noParser.push(`${q.question_id} (${r})`); continue; }
  try {
    const parsed = fn(cfg);
    if (parsed) ok.push(q.question_id);
    else fail.push(`${q.question_id} (${r})`);
  } catch (e) {
    fail.push(`${q.question_id} (${r}) EXC:${e.message}`);
  }
}
console.log(`15 专件 parser: PASS ${ok.length} / FAIL ${fail.length} / 基座链无 parser: ${noParser.length}`);
if (fail.length) { console.log("FAIL 明细（前 40）:"); fail.slice(0, 40).forEach(f => console.log("  ", f)); }
if (noParser.length) console.log("基座链:", [...new Set(noParser.map(x => x.split(" (")[1].slice(0, -1)))].join(", "));
