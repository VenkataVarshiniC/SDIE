import { describe, expect, it } from "vitest";
import { formatCompactUsd, formatUsd } from "./finance-format";

describe("finance formatting", () => {
  it("formats API decimal strings without floating labels", () => {
    expect(formatUsd("5670504.40")).toBe("$5,670,504");
  });

  it("formats chart axes in millions", () => {
    expect(formatCompactUsd(1_250_000)).toBe("$1.3m");
  });
});
