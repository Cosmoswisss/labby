// Pure filtering logic, shared by the search page and the tests.
// Filter state lives in the URL query string so any search can be shared.

import type { Language, ProjectStatus, ProjectType, SearchProject } from "./types";

export interface Filters {
  q: string;
  types: ProjectType[];
  faculties: string[];
  domains: string[];
  skills: string[];
  languages: Language[];
  statuses: ProjectStatus[];
  labs: string[];
  /** Include offers listed for an earlier semester (hidden by default). */
  includePast: boolean;
}

export const EMPTY_FILTERS: Filters = {
  q: "",
  types: [],
  faculties: [],
  domains: [],
  skills: [],
  languages: [],
  statuses: [],
  labs: [],
  includePast: false,
};

const LIST_KEYS = {
  types: "type",
  faculties: "faculty",
  domains: "domain",
  skills: "skill",
  languages: "lang",
  statuses: "status",
  labs: "lab",
} as const;

type ListKey = keyof typeof LIST_KEYS;

/** ?q=vision&type=master_thesis,semester_master&past=1 -> Filters */
export function parseFilters(params: URLSearchParams): Filters {
  const list = (name: string) =>
    (params.get(name) ?? "")
      .split(",")
      .map((v) => v.trim())
      .filter(Boolean);
  const filters: Filters = { ...EMPTY_FILTERS, q: params.get("q") ?? "" };
  for (const [key, name] of Object.entries(LIST_KEYS) as [ListKey, string][]) {
    (filters[key] as string[]) = list(name);
  }
  filters.includePast = params.get("past") === "1";
  return filters;
}

/** Filters -> query string without empty values (stable order, for shareable URLs). */
export function serializeFilters(filters: Filters): string {
  const params = new URLSearchParams();
  if (filters.q.trim()) params.set("q", filters.q.trim());
  for (const [key, name] of Object.entries(LIST_KEYS) as [ListKey, string][]) {
    const values = filters[key] as string[];
    if (values.length) params.set(name, values.join(","));
  }
  if (filters.includePast) params.set("past", "1");
  return params.toString();
}

const SEASONS: Record<string, "spring" | "fall"> = {
  spring: "spring",
  printemps: "spring",
  fall: "fall",
  autumn: "fall",
  automn: "fall",
  automne: "fall",
  winter: "fall",
};

/**
 * True when an offer's period is clearly before the current semester.
 * "Spring 2026" ends in July 2026, "Fall 2025" in January 2026, "2025-2026" in July 2026.
 * Unknown or unparseable periods are never considered past.
 */
export function isPastPeriod(period: string | null, now: Date = new Date()): boolean {
  if (!period) return false;
  const text = period.toLowerCase();
  const years = [...text.matchAll(/(20\d{2})/g)].map((m) => Number(m[1]));
  if (!years.length) return false;
  const lastYear = Math.max(...years);
  const season = Object.entries(SEASONS).find(([word]) => text.includes(word))?.[1];

  let end: Date;
  if (years.length >= 2 || text.includes("/")) {
    end = new Date(lastYear, 6, 31); // academic year: ends in July of its last year
  } else if (season === "spring") {
    end = new Date(lastYear, 6, 31);
  } else if (season === "fall") {
    end = new Date(lastYear + 1, 0, 31);
  } else {
    end = new Date(lastYear, 11, 31); // a bare year
  }
  return end < now;
}

function intersects<T>(selected: T[], values: T[]): boolean {
  return selected.length === 0 || selected.some((v) => values.includes(v));
}

/** Applies every filter except the text query (handled by the search index). */
export function applyFilters(
  projects: SearchProject[],
  filters: Filters,
  now: Date = new Date(),
): SearchProject[] {
  return projects.filter(
    (p) =>
      intersects(filters.types, p.types) &&
      intersects(filters.faculties, p.faculties) &&
      intersects(filters.domains, p.domains) &&
      intersects(filters.skills, p.skills) &&
      intersects(filters.languages, [p.language]) &&
      intersects(filters.statuses, [p.status]) &&
      intersects(
        filters.labs,
        p.labs.map((l) => l.id),
      ) &&
      (filters.includePast || !isPastPeriod(p.period, now)),
  );
}

/** Values of one facet with their counts, most frequent first. */
export function facetCounts(
  projects: SearchProject[],
  pick: (p: SearchProject) => string[],
  minCount = 1,
): { value: string; count: number }[] {
  const counts = new Map<string, number>();
  for (const p of projects) {
    for (const v of new Set(pick(p))) counts.set(v, (counts.get(v) ?? 0) + 1);
  }
  return [...counts.entries()]
    .filter(([, c]) => c >= minCount)
    .map(([value, count]) => ({ value, count }))
    .sort((a, b) => b.count - a.count || a.value.localeCompare(b.value));
}

export function toggleValue<T>(values: T[], value: T): T[] {
  return values.includes(value) ? values.filter((v) => v !== value) : [...values, value];
}

export function activeFilterCount(filters: Filters): number {
  return (
    filters.types.length +
    filters.faculties.length +
    filters.domains.length +
    filters.skills.length +
    filters.languages.length +
    filters.statuses.length +
    filters.labs.length +
    (filters.includePast ? 1 : 0)
  );
}
