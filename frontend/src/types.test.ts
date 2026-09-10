import { describe, expect, it } from "vitest";
import { expectedOutputSize, SCALES } from "./types";

describe("expectedOutputSize", () => {
  it("uses the 1080x2340 acceptance matrix", () => {
    const cases: Record<number, [number, number]> = {
      2: [2160, 4680],
      4: [4320, 9360],
      6: [6480, 14040],
      8: [8640, 18720],
      10: [10800, 23400],
    };
    for (const scale of SCALES) {
      const size = expectedOutputSize(1080, 2340, scale);
      expect([size.width, size.height]).toEqual(cases[scale]);
    }
  });

  it("never hard-codes dimensions", () => {
    expect(expectedOutputSize(13, 17, 2)).toEqual({ width: 26, height: 34 });
  });
});
