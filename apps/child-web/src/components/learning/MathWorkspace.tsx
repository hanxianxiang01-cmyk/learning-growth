export function MathWorkspace({ uiSchema }: { uiSchema: import("@/src/lib/api/contracts").TaskUiSchema }) {
  const groups =
    uiSchema.schema_version === "1.0" &&
    uiSchema.kind === "manipulative" &&
    uiSchema.visual.type === "objects"
      ? uiSchema.visual.groups
      : [];

  return (
    <div className="math-workspace">
      {!groups.length && (
        <div className="workspace-placeholder">
          在这里画一画、摆一摆，看看数学关系。
        </div>
      )}

      {groups.map((group, idx) => (
        <div className="workspace-row" key={`${group.label}-${idx}`}>
          <strong>{group.label}</strong>
          <div className="workspace-objects" aria-label={`${group.count}个`}>
            {Array.from({ length: Math.min(group.count, 20) }, (_, i) => (
              <span key={i}>{group.symbol ?? "●"}</span>
            ))}
          </div>
          <span className="workspace-count">{group.count}</span>
        </div>
      ))}
    </div>
  );
}
