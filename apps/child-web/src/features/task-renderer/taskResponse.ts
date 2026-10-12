import type { TaskInstance, TaskResponse } from "@/src/lib/api/contracts";

// Extracted without changing semantics so readiness can be tested without importing React.
export function createEmptyTaskResponse(): TaskResponse {
  return { schema_version: "1.0", answer: "", interaction_events: [] };
}

export function isTaskResponseReady(
  response: TaskResponse,
  task?: TaskInstance
) {
  const hasAnswer = String(response.answer ?? "").trim().length > 0;
  if (!hasAnswer) return false;

  if (task?.ui_schema.schema_version === "2.0") {
    return Array.isArray(response.v2_workspaces) && response.v2_workspaces.length > 0;
  }

  if (task?.ui_schema.response_schema.representation_required) {
    return Boolean(response.representation);
  }
  return true;
}
