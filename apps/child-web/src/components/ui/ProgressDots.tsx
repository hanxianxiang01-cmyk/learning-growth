export function ProgressDots({
  current,
  total
}: {
  current: number;
  total: number;
}) {
  return (
    <div className="progress-dots" aria-label={`第 ${current} / ${total} 题`}>
      {Array.from({ length: total }, (_, i) => {
        const n = i + 1;
        return (
          <span
            key={n}
            className={`progress-dot ${
              n < current ? "done" : n === current ? "current" : ""
            }`}
          />
        );
      })}
    </div>
  );
}
