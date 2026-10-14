/** Presentation flag only. This never selects content, changes a score or enables QA pin. */
export type ChildUiVersion = "legacy" | "v6";

export function resolveChildUiVersion(value?: string | null): ChildUiVersion {
  return value === "v6" ? "v6" : "legacy";
}
