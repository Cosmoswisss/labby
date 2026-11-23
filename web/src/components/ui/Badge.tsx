import type { ReactNode } from "react";
import { STATUS_LABELS, type ProjectStatus } from "@/lib/types";

const TONES = {
  primary: "bg-primary-soft text-primary-soft-fg",
  neutral: "bg-surface-muted text-fg-muted",
  success: "bg-success-soft text-success-fg",
  warning: "bg-warning-soft text-warning-fg",
} as const;

export type BadgeTone = keyof typeof TONES;

export function Badge({
  children,
  tone = "neutral",
  title,
  dot = false,
}: {
  children: ReactNode;
  tone?: BadgeTone;
  title?: string;
  dot?: boolean;
}) {
  return (
    <span
      title={title}
      className={`inline-flex shrink-0 items-center gap-1.5 rounded-full whitespace-nowrap px-2.5 py-0.5 text-xs leading-5 font-medium ${TONES[tone]}`}
    >
      {dot && <span className="size-1.5 rounded-full bg-current" aria-hidden="true" />}
      {children}
    </span>
  );
}

export function StatusBadge({ status }: { status: ProjectStatus }) {
  const tone: BadgeTone =
    status === "available" ? "success" : status === "reserved" ? "warning" : "neutral";
  return (
    <Badge tone={tone} dot>
      {STATUS_LABELS[status]}
    </Badge>
  );
}
