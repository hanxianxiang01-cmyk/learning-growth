import type { ChangeEvent, KeyboardEvent } from "react";
import { PrimaryButton } from "../ui/PrimaryButton";

export function AnswerComposer({
  value,
  placeholder,
  disabled,
  onChange,
  onSubmit
}: {
  value: string;
  placeholder?: string;
  disabled?: boolean;
  onChange: (value: string) => void;
  onSubmit: () => void;
}) {
  return (
    <div className="surface-card answer-composer">
      <label htmlFor="math-answer"><strong>我的答案</strong></label>
      <input
        id="math-answer"
        value={value}
        disabled={disabled}
        placeholder={placeholder ?? "请输入答案"}
        onChange={(e: ChangeEvent<HTMLInputElement>) => onChange(e.target.value)}
        onKeyDown={(e: KeyboardEvent<HTMLInputElement>) => {
          if (e.key === "Enter" && value.trim() && !disabled) onSubmit();
        }}
      />
      <PrimaryButton
        disabled={disabled || !value.trim()}
        onClick={onSubmit}
      >
        {disabled ? "正在判断…" : "提交答案"}
      </PrimaryButton>
    </div>
  );
}
