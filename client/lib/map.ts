import type { PostSearchBounds } from "./api";

export function locationSearchBounds(center: [number, number]): PostSearchBounds {
  const longitudeSpan = Math.min(
    180,
    0.25 / Math.max(0.01, Math.cos((center[0] * Math.PI) / 180)),
  );
  const wrap = (longitude: number) => ((longitude + 540) % 360) - 180;
  return {
    north: Math.min(90, center[0] + 0.25),
    south: Math.max(-90, center[0] - 0.25),
    east: wrap(center[1] + longitudeSpan),
    west: wrap(center[1] - longitudeSpan),
  };
}
