"use client";

import { useState } from "react";

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
  initiallyShown = 8,
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
    <fieldset className="min-w-0 border-b border-stone-200 py-4 dark:border-stone-800">
      <legend className="mb-2 text-xs font-semibold tracking-wide text-stone-500 uppercase dark:text-stone-400">
        {title}
      </legend>
      {searchable && options.length > initiallyShown && (
        <input
          type="search"
          value={needle}
          onChange={(e) => setNeedle(e.target.value)}
          placeholder={`Filter ${title.toLowerCase()}…`}
          aria-label={`Filter ${title.toLowerCase()}`}
          className="mb-2 w-full rounded-md border border-stone-300 bg-white px-2 py-1 text-sm dark:border-stone-700 dark:bg-stone-900"
        />
      )}
      <ul className="space-y-1">
        {visible.map((option) => {
          const checked = selected.includes(option.value);
          return (
            <li key={option.value}>
              <label className="flex cursor-pointer items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => onToggle(option.value)}
                  className="size-4 rounded border-stone-300 accent-accent-600"
                />
                <span className={`flex-1 truncate ${checked ? "font-medium" : ""}`}>
                  {option.label}
                </span>
                <span className="text-xs text-stone-400 tabular-nums">{option.count}</span>
              </label>
            </li>
          );
        })}
        {visible.length === 0 && <li className="text-sm text-stone-400">No match</li>}
      </ul>
      {!needle && matching.length > initiallyShown && (
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="mt-2 text-sm font-medium text-accent-700 hover:underline dark:text-accent-400"
        >
          {expanded ? "Show less" : `Show all ${matching.length}`}
        </button>
      )}
    </fieldset>
  );
}
