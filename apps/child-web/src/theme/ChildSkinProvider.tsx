"use client";

import React, { createContext, useContext } from "react";
import { v6Tokens, v6Actions } from "./v6Tokens";
import { resolveChildUiVersion, type ChildUiVersion } from "./uiVersion";
import { DEFAULT_CHILD_MATH_SKIN, skins, type ChildMathSkin } from "./skins";

const ChildUiContext = createContext<{ uiVersion: ChildUiVersion; skin: ChildMathSkin }>({ uiVersion: "legacy", skin: DEFAULT_CHILD_MATH_SKIN });
export const useChildUi = () => useContext(ChildUiContext);

function resolveSkin(value?: string | null): ChildMathSkin {
  return value === "healing" || value === "exploration-lab"
    ? value
    : DEFAULT_CHILD_MATH_SKIN;
}

export function ChildSkinProvider({
  children,
  skin,
  uiVersion = "legacy"
}: {
  children: React.ReactNode;
  skin?: string | null;
  uiVersion?: ChildUiVersion;
}) {
  const resolved = resolveSkin(skin);
  const version = resolveChildUiVersion(uiVersion);
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

  const modern = v6Tokens[resolved];
  const modernStyle = version === "v6" ? {
    "--cm-primary": v6Actions.primary,
    "--cm-primary-soft": modern.soft,
    "--cm-secondary": modern.secondary,
    "--cm-app": modern.app,
    "--cm-surface": modern.surface,
    "--cm-text": modern.text,
    "--cm-text-2": modern.text2,
    "--cm-border": modern.border,
    "--cm-success": v6Actions.success,
    "--cm-warning": v6Actions.review,
    "--cm-grid": modern.grid,
    "--cm-radius-card": "26px",
    "--cm-radius-control": "16px",
    "--cm-shadow": "0 10px 28px #2349440d",
    "--v6-theme": modern.theme,
    "--v6-edge": modern.edge,
    "--v6-action": v6Actions.primary,
    "--v6-action-hover": v6Actions.hover,
    "--v6-on-action": v6Actions.foreground,
    "--v6-disabled": v6Actions.disabled,
    "--v6-on-disabled": v6Actions.disabledForeground,
    "--v6-focus": v6Actions.focus,
    "--v6-success": v6Actions.success,
    "--v6-success-bg": v6Actions.successBackground,
    "--v6-review": v6Actions.review,
    "--v6-review-bg": v6Actions.reviewBackground,
    "--v6-retry": v6Actions.retry,
    "--v6-retry-bg": v6Actions.retryBackground
  } as React.CSSProperties : {};

  return (
    <ChildUiContext.Provider value={{ uiVersion: version, skin: resolved }}>
      <div data-child-math-skin={resolved} data-child-ui-version={version} style={{ ...style, ...modernStyle }}>
        {children}
      </div>
    </ChildUiContext.Provider>
  );
}
