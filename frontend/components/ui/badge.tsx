import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";
import type { FitStatus } from "@/lib/types";

const badgeVariants = cva(
  "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold border transition-colors",
  {
    variants: {
      variant: {
        default: "bg-gray-100 text-gray-800 border-gray-200",
        excellent: "bg-green-100 text-green-800 border-green-200",
        good: "bg-blue-100 text-blue-800 border-blue-200",
        adequate: "bg-yellow-100 text-yellow-800 border-yellow-200",
        poor: "bg-red-100 text-red-800 border-red-200",
        outline: "border border-gray-300 text-gray-700",
        secondary: "bg-purple-100 text-purple-800 border-purple-200",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

function FitStatusBadge({ status }: { status: FitStatus }) {
  const config: Record<FitStatus, { label: string; emoji: string; variant: BadgeProps["variant"] }> = {
    EXCELLENT: { label: "Excellent", emoji: "🟢", variant: "excellent" },
    GOOD: { label: "Good", emoji: "🔵", variant: "good" },
    ADEQUATE: { label: "Adequate", emoji: "🟡", variant: "adequate" },
    POOR: { label: "Poor", emoji: "🔴", variant: "poor" },
  };
  const { label, emoji, variant } = config[status];
  return (
    <Badge variant={variant}>
      {emoji} {label}
    </Badge>
  );
}

export { Badge, FitStatusBadge, badgeVariants };
