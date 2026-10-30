import type { ChildMathSkin } from "./skins";

/** V6 presentation tokens. Production skin identifiers remain unchanged. */
export const v6Tokens = {
  "exploration-lab": {
    app: "#edf8ff", surface: "#ffffff", text: "#1b2b37", text2: "#4c5f6b",
    border: "#d0e1ea", edge: "#8296a0", soft: "#e7f3f4", accent: "#e6a34a",
    theme: "#337ac3", secondary: "#268b9d", grid: "#e6f0f6"
  },
  healing: {
    app: "#fcfaf1", surface: "#fffefb", text: "#24352e", text2: "#55675c",
    border: "#d9e1ce", edge: "#859687", soft: "#edf4e8", accent: "#b48868",
    theme: "#2b6e55", secondary: "#43866e", grid: "#edf1e6"
  }
} satisfies Record<ChildMathSkin, Record<string, string>>;

export const v6Actions = {
  primary: "#0a6972", hover: "#07575e", foreground: "#ffffff",
  disabled: "#e6ecee", disabledForeground: "#52636a", focus: "#245fcc",
  success: "#19714e", successBackground: "#edf7f0",
  review: "#875314", reviewBackground: "#fff5e7",
  retry: "#0a6972", retryBackground: "#eaf5f5"
} as const;
