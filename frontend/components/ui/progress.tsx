import * as React from "react";
import { cn } from "@/lib/utils";

interface ProgressProps {
  value: number; // 0-100
  className?: string;
  showLabel?: boolean;
  color?: "blue" | "green" | "yellow" | "red";
  size?: "sm" | "md" | "lg";
}

export function Progress({
  value,
  className,
  showLabel = false,
  color = "blue",
  size = "md",
}: ProgressProps) {
  const clampedValue = Math.max(0, Math.min(100, value));

  const colorClasses = {
    blue: "bg-blue-500",
    green: "bg-green-500",
    yellow: "bg-yellow-500",
    red: "bg-red-500",
  };

  const sizeClasses = {
    sm: "h-1.5",
    md: "h-2.5",
    lg: "h-4",
  };

  return (
    <div className={cn("w-full", className)}>
      {showLabel && (
        <div className="flex justify-between mb-1">
          <span className="text-xs text-gray-600">Progress</span>
          <span className="text-xs font-medium text-gray-900">
            {clampedValue}%
          </span>
        </div>
      )}
      <div
        className={cn("w-full bg-gray-200 rounded-full overflow-hidden", sizeClasses[size])}
      >
        <div
          className={cn(
            "h-full rounded-full transition-all duration-300 ease-out",
            colorClasses[color]
          )}
          style={{ width: `${clampedValue}%` }}
        />
      </div>
    </div>
  );
}

interface ScoreBarProps {
  label: string;
  score: number;
  weight?: number;
}

export function ScoreBar({ label, score, weight }: ScoreBarProps) {
  const color =
    score >= 80 ? "green" : score >= 60 ? "blue" : score >= 40 ? "yellow" : "red";

  return (
    <div className="space-y-1">
      <div className="flex justify-between items-center">
        <span className="text-xs text-gray-600">
          {label}
          {weight && (
            <span className="ml-1 text-gray-400">({weight}%)</span>
          )}
        </span>
        <span className="text-xs font-semibold text-gray-900">{score}</span>
      </div>
      <Progress value={score} color={color} size="sm" />
    </div>
  );
}
