"use client";

import type { Filters } from "@/lib/filters";
import { LANGUAGE_LABELS, PROJECT_TYPE_LABELS, STATUS_LABELS } from "@/lib/types";
import { Icon } from "../ui/Icon";

export type ListFacet =
  | "types"
  | "topics"
  | "faculties"
  | "domains"
  | "skills"
  | "languages"
  | "statuses"
  | "labs";

const LABELERS: Record<ListFacet, (v: string, labNames: Record<string, string>) => string> = {
  types: (v) => PROJECT_TYPE_LABELS[v as keyof typeof PROJECT_TYPE_LABELS] ?? v,
  topics: (v) => v,
  faculties: (v) => v,
  domains: (v) => v,
  skills: (v) => v,
  languages: (v) => LANGUAGE_LABELS[v as keyof typeof LANGUAGE_LABELS] ?? v,
  statuses: (v) => STATUS_LABELS[v as keyof typeof STATUS_LABELS] ?? v,
  labs: (v, labNames) => labNames[v]?.split(" — ")[0] ?? v,
};

/** Removable chips for every active filter, shown above the results. */
export function ActiveFilters({
  filters,
  labNames,
  onRemove,
  onTogglePast,
  onClearAll,
}: {
  filters: Filters;
  labNames: Record<string, string>;
  onRemove: (key: ListFacet, value: string) => void;
  onTogglePast: () => void;
  onClearAll: () => void;
}) {
  const chips: { key: string; label: string; remove: () => void }[] = [];
  for (const key of Object.keys(LABELERS) as ListFacet[]) {
    for (const value of filters[key] as string[]) {
      chips.push({
        key: `${key}:${value}`,
        label: LABELERS[key](value, labNames),
        remove: () => onRemove(key, value),
      });
    }
  }
  if (filters.includePast) {
    chips.push({ key: "past", label: "Including past semesters", remove: onTogglePast });
  }
  if (!chips.length && !filters.q) return null;

  return (
    <div className="mb-5 flex flex-wrap items-center gap-2" aria-label="Active filters">
      {chips.map((chip) => (
        <button
          key={chip.key}
          type="button"
          onClick={chip.remove}
          aria-label={`Remove filter: ${chip.label}`}
          className="group inline-flex items-center gap-1.5 rounded-full bg-primary-soft py-1 pr-2 pl-3 text-sm font-medium text-primary-soft-fg transition-all duration-200 hover:brightness-95 active:scale-95 dark:hover:brightness-125"
        >
          {chip.label}
          <Icon name="x" className="size-3.5 opacity-70 group-hover:opacity-100" strokeWidth={2.2} />
        </button>
      ))}
      <button
        type="button"
        onClick={onClearAll}
        className="rounded-full px-3 py-1 text-sm font-medium text-fg-muted transition-colors duration-200 hover:bg-surface-muted hover:text-fg"
      >
        Clear all
      </button>
    </div>
  );
}
