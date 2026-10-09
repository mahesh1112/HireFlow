import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import type { FitStatus } from "@/lib/types";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function getFitStatusColor(status: FitStatus): string {
  const colors: Record<FitStatus, string> = {
    EXCELLENT: "score-excellent",
    GOOD: "score-good",
    ADEQUATE: "score-adequate",
    POOR: "score-poor",
  };
  return colors[status];
}

export function getFitStatusLabel(status: FitStatus): string {
  const labels: Record<FitStatus, string> = {
    EXCELLENT: "Excellent",
    GOOD: "Good",
    ADEQUATE: "Adequate",
    POOR: "Poor",
  };
  return labels[status];
}

export function getFitStatusFromScore(score: number): FitStatus {
  if (score >= 86) return "EXCELLENT";
  if (score >= 61) return "GOOD";
  if (score >= 31) return "ADEQUATE";
  return "POOR";
}

export function getFitStatusEmoji(status: FitStatus): string {
  const emojis: Record<FitStatus, string> = {
    EXCELLENT: "🟢",
    GOOD: "🔵",
    ADEQUATE: "🟡",
    POOR: "🔴",
  };
  return emojis[status];
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export function truncate(str: string, maxLen: number): string {
  if (str.length <= maxLen) return str;
  return str.slice(0, maxLen) + "...";
}

export function downloadCSV(data: Record<string, unknown>[], filename: string) {
  if (!data.length) return;
  const headers = Object.keys(data[0]);
  const csvRows = [
    headers.join(","),
    ...data.map((row) =>
      headers
        .map((h) => {
          const val = String(row[h] ?? "").replace(/"/g, '""');
          return `"${val}"`;
        })
        .join(",")
    ),
  ];
  const csvContent = csvRows.join("\n");
  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export function getScoreColor(score: number): string {
  if (score >= 86) return "text-green-600";
  if (score >= 61) return "text-blue-600";
  if (score >= 31) return "text-yellow-600";
  return "text-red-600";
}

export function getScoreBgColor(score: number): string {
  if (score >= 86) return "bg-green-100";
  if (score >= 61) return "bg-blue-100";
  if (score >= 31) return "bg-yellow-100";
  return "bg-red-100";
}
