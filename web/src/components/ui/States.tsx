import type { ReactNode } from "react";
import { Icon, type IconName } from "./Icon";

/** Grey placeholder block, pulsing gently while content loads. */
export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-shimmer rounded-md bg-surface-muted ${className}`} />;
}

export function ProjectCardSkeleton() {
  return (
    <div className="rounded-xl border border-border bg-surface p-5 shadow-soft sm:p-6">
      <Skeleton className="h-3.5 w-24" />
      <Skeleton className="mt-4 h-5 w-4/5" />
      <Skeleton className="mt-3 h-3.5 w-full" />
      <Skeleton className="mt-2 h-3.5 w-2/3" />
      <div className="mt-5 flex gap-2">
        <Skeleton className="h-6 w-20 rounded-full" />
        <Skeleton className="h-6 w-24 rounded-full" />
      </div>
    </div>
  );
}

export function EmptyState({
  icon = "search",
  title,
  description,
  action,
}: {
  icon?: IconName;
  title: string;
  description?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center rounded-xl border border-dashed border-border-strong bg-surface px-6 py-14 text-center">
      <span className="flex size-12 items-center justify-center rounded-full bg-primary-soft text-primary-soft-fg">
        <Icon name={icon} className="size-6" />
      </span>
      <h2 className="mt-5 text-lg font-semibold">{title}</h2>
      {description && <p className="mt-2 max-w-md text-fg-muted">{description}</p>}
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
}
