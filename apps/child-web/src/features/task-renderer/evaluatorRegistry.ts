import type { RendererProtocolId } from "./rendererRegistry";
import { evaluateRendererAnswer, type RendererEvaluation, type RendererEvidence } from "./rendererContract";

export type RendererEvaluator = (input: {
  answer: string;
  evidence: RendererEvidence;
  config: Record<string, unknown>;
}) => RendererEvaluation;

const genericEvaluator = (rendererId: RendererProtocolId): RendererEvaluator => ({ answer, evidence, config }) =>
  evaluateRendererAnswer(`${rendererId}.generic`, answer, evidence, config.expected_answer ?? config.answer);

export const RENDERER_EVALUATORS: Record<RendererProtocolId, RendererEvaluator> = {
  "object-counter": genericEvaluator("object-counter"),
  "bar-model": genericEvaluator("bar-model"),
  "number-line": genericEvaluator("number-line"),
  "number-input": genericEvaluator("number-input"),
  "choice-grid": genericEvaluator("choice-grid"),
  "place-value": genericEvaluator("place-value"),
  "ten-frame": genericEvaluator("ten-frame"),
  "column-arithmetic": genericEvaluator("column-arithmetic"),
  "array-board": genericEvaluator("array-board"),
  "grouping-board": genericEvaluator("grouping-board"),
  "formula-board": genericEvaluator("formula-board"),
  "estimation-canvas": genericEvaluator("estimation-canvas"),
  "shape-gallery": genericEvaluator("shape-gallery"),
  "shape-canvas": genericEvaluator("shape-canvas"),
  "sorting-board": genericEvaluator("sorting-board"),
  "direction-grid": genericEvaluator("direction-grid"),
  "ruler": genericEvaluator("ruler"),
  "clock": genericEvaluator("clock"),
  "timeline": genericEvaluator("timeline"),
  "money-board": genericEvaluator("money-board"),
  "data-table": genericEvaluator("data-table"),
  "pictograph": genericEvaluator("pictograph"),
  "pattern-board": genericEvaluator("pattern-board")
};

export function getRendererEvaluator(rendererId: RendererProtocolId) {
  return RENDERER_EVALUATORS[rendererId];
}
