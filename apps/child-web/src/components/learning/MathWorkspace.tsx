import type { TaskUiSchema } from "@/src/lib/api/contracts";

export function MathWorkspace({
  uiSchema
}: {
  uiSchema: TaskUiSchema;
}) {
  const visual = uiSchema.visual;
  return (
    <div className="math-workspace">
      {!visual?.rows?.length && (
        <div className="workspace-placeholder">
          在这里画一画、摆一摆，看看数学关系。
        </div>
      )}

      {visual?.rows?.map((row, idx) => (
        <div className="workspace-row" key={`${row.label}-${idx}`}>
          <strong>{row.label}</strong>
          <div className="workspace-objects" aria-label={`${row.count}个`}>
            {Array.from({ length: Math.min(row.count, 20) }, (_, i) => (
              <span key={i}>{row.symbol ?? "●"}</span>
            ))}
          </div>
          <span className="workspace-count">{row.count}</span>
        </div>
      ))}
    </div>
  );
}
