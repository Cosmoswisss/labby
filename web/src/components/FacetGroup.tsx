"use client";

import { useId, useState } from "react";
import { Icon } from "./ui/Icon";

export interface FacetOption {
  value: string;
  label: string;
  count: number;
}

/** A list of checkboxes with counts; long lists are truncated with a filter box. */
export function FacetGroup({
  title,
  options,
  selected,
  onToggle,
  initiallyShown = 6,
  searchable = false,
}: {
  title: string;
  options: FacetOption[];
  selected: string[];
  onToggle: (value: string) => void;
  initiallyShown?: number;
  searchable?: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const [needle, setNeedle] = useState("");
  const id = useId();

  const matching = needle
    ? options.filter((o) => o.label.toLowerCase().includes(needle.toLowerCase()))
    : options;
  // Selected values always stay visible, even when the list is collapsed.
  const visible =
    expanded || needle
      ? matching
      : [
          ...matching.slice(0, initiallyShown),
          ...matching.slice(initiallyShown).filter((o) => selected.includes(o.value)),
        ];

  if (options.length === 0 && selected.length === 0) return null;

  return (
    <fieldset className="min-w-0 border-b border-border py-5 last:border-b-0">
      <legend className="float-left mb-3 w-full text-sm font-semibold text-fg">
        {title}
        {selected.length > 0 && (
          <span className="ml-2 rounded-full bg-primary-soft px-2 py-0.5 text-xs font-medium text-primary-soft-fg">
            {selected.length}
          </span>
        )}
      </legend>

      {searchable && options.length > initiallyShown && (
        <div className="relative clear-both mb-2">
          <label htmlFor={`${id}-filter`} className="sr-only">
            Filter {title.toLowerCase()} options
          </label>
          <Icon
            name="search"
            className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-fg-subtle"
          />
          <input
            id={`${id}-filter`}
            type="search"
            value={needle}
            onChange={(e) => setNeedle(e.target.value)}
            placeholder={`Find in ${title.toLowerCase()}…`}
            className="h-9 w-full rounded-lg border border-border bg-surface pr-2 pl-8 text-sm text-fg transition-all duration-200 placeholder:text-fg-subtle hover:border-border-strong focus:border-primary focus:outline-none"
          />
        </div>
      )}

      <ul className="clear-both space-y-0.5">
        {visible.map((option) => {
          const checked = selected.includes(option.value);
          const inputId = `${id}-${option.value}`;
          return (
            <li key={option.value}>
              <label
                htmlFor={inputId}
                className="group flex cursor-pointer items-center gap-3 rounded-lg px-2 py-1.5 text-sm transition-colors duration-200 hover:bg-surface-muted"
              >
                <input
                  id={inputId}
                  type="checkbox"
                  checked={checked}
                  onChange={() => onToggle(option.value)}
                  className="size-4 shrink-0 cursor-pointer accent-[var(--primary)]"
                />
                <span
                  className={`min-w-0 flex-1 leading-snug ${
                    checked ? "font-medium text-fg" : "text-fg-muted group-hover:text-fg"
                  }`}
                >
                  {option.label}
                </span>
                <span className="text-xs text-fg-subtle tabular-nums">{option.count}</span>
              </label>
            </li>
          );
        })}
        {visible.length === 0 && <li className="px-2 py-1.5 text-sm text-fg-subtle">No match</li>}
      </ul>

      {!needle && matching.length > initiallyShown && (
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          aria-expanded={expanded}
          className="mt-2 rounded-md px-2 py-1 text-sm font-medium text-primary-text transition-colors duration-200 hover:bg-primary-soft"
        >
          {expanded ? "Show less" : `Show all ${matching.length}`}
        </button>
      )}
    </fieldset>
  );
}
