export type ChildMathSkin = "healing" | "exploration-lab";
export const DEFAULT_CHILD_MATH_SKIN: ChildMathSkin = "exploration-lab";

export const skins = {
  healing: {
    id: "healing",
    label: "轻量治愈",
    primary: "#4C9B82",
    primarySoft: "#EAF6F0",
    secondary: "#7AB7E8",
    app: "#F8FBF7",
    surface: "#FFFFFF",
    text: "#264157",
    text2: "#718293",
    border: "#DFEBE4",
    success: "#56B989",
    warning: "#F4C55D",
    grid: "#ECF3EE",
    radiusCard: "28px",
    radiusControl: "18px",
    shadow: "0 8px 28px rgba(77,126,111,.09)"
  },
  "exploration-lab": {
    id: "exploration-lab",
    label: "探索实验室",
    primary: "#287AD8",
    primarySoft: "#E6F1FD",
    secondary: "#49B39F",
    app: "#F1F7FD",
    surface: "#FFFFFF",
    text: "#163554",
    text2: "#60758B",
    border: "#CFE0EF",
    success: "#3FAF7C",
    warning: "#F3B94F",
    grid: "#D5E6F4",
    radiusCard: "18px",
    radiusControl: "14px",
    shadow: "0 8px 22px rgba(27,78,124,.10)"
  }
} as const;
