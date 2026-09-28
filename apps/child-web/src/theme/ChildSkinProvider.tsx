"use client";

import React from "react";
import { DEFAULT_CHILD_MATH_SKIN, skins, type ChildMathSkin } from "./skins";

function resolveSkin(value?: string | null): ChildMathSkin {
  return value === "healing" || value === "math-lab"
    ? value
    : DEFAULT_CHILD_MATH_SKIN;
}

export function ChildSkinProvider({
  children,
  skin
}: {
  children: React.ReactNode;
  skin?: string | null;
}) {
  const resolved = resolveSkin(skin);
  const t = skins[resolved];

  const style = {
    "--cm-primary": t.primary,
    "--cm-primary-soft": t.primarySoft,
    "--cm-secondary": t.secondary,
    "--cm-app": t.app,
    "--cm-surface": t.surface,
    "--cm-text": t.text,
    "--cm-text-2": t.text2,
    "--cm-border": t.border,
    "--cm-success": t.success,
    "--cm-warning": t.warning,
    "--cm-grid": t.grid,
    "--cm-radius-card": t.radiusCard,
    "--cm-radius-control": t.radiusControl,
    "--cm-shadow": t.shadow
  } as React.CSSProperties;

  return (
    <div data-child-math-skin={resolved} style={style}>
      {children}
    </div>
  );
}
