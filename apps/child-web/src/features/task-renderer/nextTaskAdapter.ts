import type { AttemptResult, TaskInstance } from "@/src/lib/api/contracts";

/** Backend remains authoritative for recommendation/next-task selection. */
export type NextTaskBoundary = {
  diagnosis_code?: string;
  next_action: AttemptResult["next_action"];
  task_instance?: TaskInstance;
};

export function buildNextTaskBoundary(result: AttemptResult, task?: TaskInstance): NextTaskBoundary {
  return {
    diagnosis_code: result.diagnosis?.code,
    next_action: result.next_action,
    task_instance: task
  };
}
