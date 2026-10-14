/** UI geometry only; clockV2 remains the state / serializer / evidence authority. */
export type ClockHand = "hour" | "minute";
export const CLOCK_DRAG_THRESHOLD_PX = 7;

export function clockDragStarted(startX: number, startY: number, x: number, y: number): boolean {
  return Math.hypot(x - startX, y - startY) >= CLOCK_DRAG_THRESHOLD_PX;
}

/** x/y are in a 360×360 viewBox. A center dead-zone prevents angle jumps. */
export function clockValueFromPoint(hand: ClockHand, x: number, y: number, minute: number): number | null {
  if (![x, y, minute].every(Number.isFinite) || ![0, 30].includes(minute)) return null;
  const dx = x - 180, dy = y - 180;
  if (Math.hypot(dx, dy) < 28) return null;
  const degrees = (Math.atan2(dx, -dy) * 180 / Math.PI + 360) % 360;
  if (hand === "minute") return degrees >= 90 && degrees < 270 ? 30 : 0;
  return ((Math.round((degrees - minute * 0.5) / 30) % 12) + 12) % 12 || 12;
}

/** Bounded slider semantics, never a five-minute state. */
export function clockKeyValue(hand: ClockHand, current: number, key: string): number | null {
  const max = hand === "hour" ? 12 : 30, min = hand === "hour" ? 1 : 0;
  if (key === "Home") return min;
  if (key === "End") return max;
  if (!["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(key)) return null;
  const increase = key === "ArrowRight" || key === "ArrowUp";
  return hand === "minute" ? (increase ? 30 : 0) : Math.max(min, Math.min(max, current + (increase ? 1 : -1)));
}
