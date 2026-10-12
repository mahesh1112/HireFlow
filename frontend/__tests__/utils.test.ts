import {
  getFitStatusFromScore,
  getFitStatusColor,
  getFitStatusEmoji,
  formatFileSize,
  getScoreColor,
  truncate,
} from "@/lib/utils";

describe("getFitStatusFromScore", () => {
  it("returns EXCELLENT for scores 86-100", () => {
    expect(getFitStatusFromScore(100)).toBe("EXCELLENT");
    expect(getFitStatusFromScore(86)).toBe("EXCELLENT");
    expect(getFitStatusFromScore(92)).toBe("EXCELLENT");
  });

  it("returns GOOD for scores 61-85", () => {
    expect(getFitStatusFromScore(85)).toBe("GOOD");
    expect(getFitStatusFromScore(61)).toBe("GOOD");
    expect(getFitStatusFromScore(75)).toBe("GOOD");
  });

  it("returns ADEQUATE for scores 31-60", () => {
    expect(getFitStatusFromScore(60)).toBe("ADEQUATE");
    expect(getFitStatusFromScore(31)).toBe("ADEQUATE");
    expect(getFitStatusFromScore(45)).toBe("ADEQUATE");
  });

  it("returns POOR for scores 0-30", () => {
    expect(getFitStatusFromScore(30)).toBe("POOR");
    expect(getFitStatusFromScore(0)).toBe("POOR");
    expect(getFitStatusFromScore(15)).toBe("POOR");
  });
});

describe("getFitStatusColor", () => {
  it("maps EXCELLENT to green class", () => {
    expect(getFitStatusColor("EXCELLENT")).toBe("score-excellent");
  });
  it("maps GOOD to blue class", () => {
    expect(getFitStatusColor("GOOD")).toBe("score-good");
  });
  it("maps ADEQUATE to yellow class", () => {
    expect(getFitStatusColor("ADEQUATE")).toBe("score-adequate");
  });
  it("maps POOR to red class", () => {
    expect(getFitStatusColor("POOR")).toBe("score-poor");
  });
});

describe("getFitStatusEmoji", () => {
  it("returns correct emojis", () => {
    expect(getFitStatusEmoji("EXCELLENT")).toBe("🟢");
    expect(getFitStatusEmoji("GOOD")).toBe("🔵");
    expect(getFitStatusEmoji("ADEQUATE")).toBe("🟡");
    expect(getFitStatusEmoji("POOR")).toBe("🔴");
  });
});

describe("formatFileSize", () => {
  it("formats bytes correctly", () => {
    expect(formatFileSize(500)).toBe("500 B");
    expect(formatFileSize(1536)).toBe("1.5 KB");
    expect(formatFileSize(1572864)).toBe("1.5 MB");
  });
});

describe("getScoreColor", () => {
  it("returns green for scores >= 86", () => {
    expect(getScoreColor(90)).toBe("text-green-600");
    expect(getScoreColor(86)).toBe("text-green-600");
  });
  it("returns blue for scores 61-85", () => {
    expect(getScoreColor(70)).toBe("text-blue-600");
  });
  it("returns yellow for scores 31-60", () => {
    expect(getScoreColor(50)).toBe("text-yellow-600");
  });
  it("returns red for scores <= 30", () => {
    expect(getScoreColor(20)).toBe("text-red-600");
  });
});

describe("truncate", () => {
  it("returns the string unchanged if within limit", () => {
    expect(truncate("hello", 10)).toBe("hello");
  });

  it("truncates and appends ellipsis if too long", () => {
    expect(truncate("hello world", 5)).toBe("hello...");
  });
});
