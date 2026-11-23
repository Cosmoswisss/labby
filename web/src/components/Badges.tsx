import type { ReactNode } from "react";
import { STATUS_LABELS, type ProjectStatus } from "@/lib/types";

const TONES = {
  default:
    "bg-accent-50 text-accent-900 ring-accent-100 dark:bg-accent-900/40 dark:text-accent-100 dark:ring-accent-900",
  muted:
    "bg-stone-100 text-stone-700 ring-stone-200 dark:bg-stone-800 dark:text-stone-300 dark:ring-stone-700",
  green:
    "bg-emerald-50 text-emerald-800 ring-emerald-200 dark:bg-emerald-900/40 dark:text-emerald-200 dark:ring-emerald-800",
  amber:
    "bg-amber-50 text-amber-800 ring-amber-200 dark:bg-amber-900/40 dark:text-amber-200 dark:ring-amber-800",
};

export function Badge({
  children,
  tone = "default",
  title,
}: {
  children: ReactNode;
  tone?: keyof typeof TONES;
  title?: string;
}) {
  return (
    <span
      title={title}
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${TONES[tone]}`}
    >
      {children}
    </span>
  );
}

export function StatusBadge({ status }: { status: ProjectStatus }) {
  const tone = status === "available" ? "green" : status === "reserved" ? "amber" : "muted";
  return <Badge tone={tone}>{STATUS_LABELS[status]}</Badge>;
}
