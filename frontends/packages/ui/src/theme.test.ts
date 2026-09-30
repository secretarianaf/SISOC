import { expect, it } from "vitest";
import { getTheme } from "./theme";

function luminance(hex: string) {
  const channels = hex.slice(1).match(/../g)!.map((value) => parseInt(value, 16) / 255)
    .map((value) => value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4);
  return channels.reduce((sum, value, index) => sum + value * [0.2126, 0.7152, 0.0722][index], 0);
}

function contrast(first: string, second: string) {
  const values = [luminance(first), luminance(second)].sort((a, b) => a - b);
  return (values[1] + 0.05) / (values[0] + 0.05);
}

it.each(["light", "dark"] as const)("cumple contraste AA de controles y títulos en %s", (mode) => {
  const { palette } = getTheme(mode);
  expect(contrast(palette.input.outlinedBorder!, palette.background.paper)).toBeGreaterThanOrEqual(3);
  expect(contrast(palette.primary.text!, palette.background.default)).toBeGreaterThanOrEqual(4.5);
  expect(contrast(palette.primary.main, palette.background.paper)).toBeGreaterThanOrEqual(3);
});
