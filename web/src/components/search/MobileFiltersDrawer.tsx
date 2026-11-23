"use client";

import { useEffect, useRef, type ReactNode } from "react";
import { Button } from "../ui/Button";
import { Icon } from "../ui/Icon";

/** Full-height side panel holding the filters on small screens (modal dialog). */
export function MobileFiltersDrawer({
  open,
  onClose,
  resultCount,
  children,
}: {
  open: boolean;
  onClose: () => void;
  resultCount: number;
  children: ReactNode;
}) {
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    const previous = document.activeElement as HTMLElement | null;
    closeRef.current?.focus();
    document.body.style.overflow = "hidden";
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", onKey);
      previous?.focus();
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 lg:hidden">
      <div
        className="animate-fade-in absolute inset-0 bg-black/40 backdrop-blur-[2px]"
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="filters-title"
        className="animate-slide-in absolute inset-y-0 right-0 flex w-full max-w-sm flex-col bg-surface shadow-lift"
      >
        <div className="flex h-16 items-center justify-between border-b border-border px-5">
          <h2 id="filters-title" className="text-lg font-semibold">
            Filters
          </h2>
          <button
            ref={closeRef}
            type="button"
            onClick={onClose}
            aria-label="Close filters"
            className="flex size-10 items-center justify-center rounded-[10px] text-fg-muted transition-all duration-200 hover:bg-surface-muted hover:text-fg"
          >
            <Icon name="x" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-5">{children}</div>
        <div className="border-t border-border p-4">
          <Button size="lg" className="w-full" onClick={onClose}>
            Show {resultCount} {resultCount === 1 ? "project" : "projects"}
          </Button>
        </div>
      </div>
    </div>
  );
}
