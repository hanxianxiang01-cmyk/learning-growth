import type { AttemptResult, DiagnosisResult } from "@/src/lib/api/contracts";
import type { RendererEvidence } from "./rendererContract";

/**
 * Diagnosis is a backend/learning-engine decision. The frontend only packages
 * renderer evidence and exposes a typed boundary; it never infers mastery.
 */
export type DiagnosisInput = {
  task_instance_id: string;
  renderer_id: string;
  attempt_no: number;
  evidence: RendererEvidence[];
};

export type DiagnosisOutput = {
  diagnosis?: DiagnosisResult | null;
  next_action?: AttemptResult["next_action"];
};

export function buildDiagnosisInput(
  taskInstanceId: string,
  attemptNo: number,
  evidence: RendererEvidence[]
): DiagnosisInput {
  return {
    task_instance_id: taskInstanceId,
    renderer_id: evidence[0]?.renderer_id ?? "unsupported",
    attempt_no: attemptNo,
    evidence
  };
}

export function normalizeDiagnosisBoundary(result: AttemptResult): DiagnosisOutput {
  return {
    diagnosis: result.diagnosis ?? null,
    next_action: result.next_action
  };
}
