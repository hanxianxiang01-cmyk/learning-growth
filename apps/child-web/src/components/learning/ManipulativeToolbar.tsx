export type MathTool = "draw" | "blocks" | "count" | "undo" | "clear";

const labels: Record<MathTool, string> = {
  draw: "✏️ 画一画",
  blocks: "🧱 摆一摆",
  count: "🔢 数一数",
  undo: "↶ 撤销",
  clear: "🧹 清空"
};

export function ManipulativeToolbar({
  tools = ["draw", "blocks", "count"],
  active,
  onSelect
}: {
  tools?: MathTool[];
  active?: MathTool;
  onSelect?: (tool: MathTool) => void;
}) {
  return (
    <div className="surface-card manipulative-toolbar">
      <strong>数学工具</strong>
      {tools.map(tool => (
        <button
          key={tool}
          className={`tool-button ${active === tool ? "active" : ""}`}
          onClick={() => onSelect?.(tool)}
          type="button"
        >
          {labels[tool]}
        </button>
      ))}
    </div>
  );
}
