"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import {
  EMPTY_FILTERS,
  type Filters,
  activeFilterCount,
  applyFilters,
  facetCounts,
  isPastPeriod,
  parseFilters,
  serializeFilters,
  toggleValue,
} from "@/lib/filters";
import { useClientNow } from "@/lib/client";
import { buildIndex, searchIds } from "@/lib/search";
import {
  LANGUAGE_LABELS,
  PROJECT_TYPE_LABELS,
  STATUS_LABELS,
  type Language,
  type ProjectStatus,
  type ProjectType,
  type SearchProject,
} from "@/lib/types";
import { FacetGroup, type FacetOption } from "./FacetGroup";
import { ProjectCard } from "./ProjectCard";

const PAGE_SIZE = 30;
const FACULTY_ORDER = ["IC", "STI", "SB", "SV", "ENAC", "CDM", "CDH", "ENT", "OTHER"];
const TYPE_ORDER = ["semester_bachelor", "semester_master", "master_thesis", "other"];
const STATUS_ORDER = ["available", "reserved", "unknown"];
const LANGUAGE_ORDER = ["EN", "FR", "unknown"];

/** Fixed order for short facets, so options never jump under the cursor. */
function byOrder(order: string[]) {
  return (a: FacetOption, b: FacetOption) => order.indexOf(a.value) - order.indexOf(b.value);
}

type ListFacet = "types" | "faculties" | "domains" | "skills" | "languages" | "statuses" | "labs";

export function SearchApp({
  projects,
  labNames,
}: {
  projects: SearchProject[];
  labNames: Record<string, string>;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const filters = useMemo(() => parseFilters(new URLSearchParams(searchParams.toString())), [searchParams]);

  // The text box updates instantly; the URL (and the results) follow after a short pause.
  const [query, setQuery] = useState(filters.q);
  const [shown, setShown] = useState(PAGE_SIZE);
  const now = useClientNow();

  function update(next: Filters) {
    const qs = serializeFilters(next);
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    setShown(PAGE_SIZE);
  }

  useEffect(() => {
    if (query === filters.q) return;
    const timer = setTimeout(() => update({ ...filters, q: query }), 250);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query]);

  const index = useMemo(() => buildIndex(projects), [projects]);
  const byId = useMemo(() => new Map(projects.map((p) => [p.id, p])), [projects]);

  // Text search first (keeps relevance order), then the facet filters.
  const textMatches = useMemo(() => {
    const ids = searchIds(index, filters.q);
    return ids === null ? projects : ids.map((id) => byId.get(id)!).filter(Boolean);
  }, [index, byId, projects, filters.q]);

  const reference = now ?? new Date(0); // before mount: no "past" filtering (stable SSR output)
  const results = useMemo(
    () => applyFilters(textMatches, filters, reference),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [textMatches, filters, now],
  );

  /** Counts for one facet = results of every *other* filter (standard drill-down). */
  function options(key: ListFacet, pick: (p: SearchProject) => string[], label: (v: string) => string, min = 1): FacetOption[] {
    const base = applyFilters(textMatches, { ...filters, [key]: [] }, reference);
    return facetCounts(base, pick, min).map((c) => ({ ...c, label: label(c.value) }));
  }

  function toggle(key: ListFacet, value: string) {
    update({ ...filters, [key]: toggleValue(filters[key] as string[], value) });
  }

  const facultyOptions = options("faculties", (p) => p.faculties, (v) => v).sort(byOrder(FACULTY_ORDER));
  const typeOptions = options("types", (p) => p.types, (v) => PROJECT_TYPE_LABELS[v as ProjectType]).sort(byOrder(TYPE_ORDER));
  const statusOptions = options("statuses", (p) => [p.status], (v) => STATUS_LABELS[v as ProjectStatus]).sort(byOrder(STATUS_ORDER));
  const languageOptions = options("languages", (p) => [p.language], (v) => LANGUAGE_LABELS[v as Language]).sort(byOrder(LANGUAGE_ORDER));
  const domainOptions = options("domains", (p) => p.domains, (v) => v);
  const skillOptions = options("skills", (p) => p.skills, (v) => v);
  const labOptions = options("labs", (p) => p.labs.map((l) => l.id), (v) => labNames[v] ?? v);

  const active = activeFilterCount(filters);
  const pastHidden = useMemo(
    () => (filters.includePast || !now ? 0 : applyFilters(textMatches, { ...filters, includePast: true }, now).length - results.length),
    [filters, textMatches, results.length, now],
  );

  const facetPanel = (
    <div>
      <FacetGroup title="Project type" options={typeOptions} selected={filters.types} onToggle={(v) => toggle("types", v)} />
      <FacetGroup title="Faculty" options={facultyOptions} selected={filters.faculties} onToggle={(v) => toggle("faculties", v)} />
      <FacetGroup title="Domain" options={domainOptions} selected={filters.domains} onToggle={(v) => toggle("domains", v)} searchable />
      <FacetGroup title="Skills" options={skillOptions} selected={filters.skills} onToggle={(v) => toggle("skills", v)} searchable />
      <FacetGroup title="Lab" options={labOptions} selected={filters.labs} onToggle={(v) => toggle("labs", v)} searchable initiallyShown={6} />
      <FacetGroup title="Status" options={statusOptions} selected={filters.statuses} onToggle={(v) => toggle("statuses", v)} />
      <FacetGroup title="Language" options={languageOptions} selected={filters.languages} onToggle={(v) => toggle("languages", v)} />
      <label className="flex cursor-pointer items-center gap-2 py-4 text-sm">
        <input
          type="checkbox"
          checked={filters.includePast}
          onChange={() => update({ ...filters, includePast: !filters.includePast })}
          className="size-4 accent-accent-600"
        />
        Include offers from past semesters
      </label>
    </div>
  );

  return (
    <div>
      <section className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">
          Find a semester project or master thesis
        </h1>
        <p className="mt-1 text-stone-600 dark:text-stone-400">
          {projects.length} projects from {Object.keys(labNames).length} EPFL labs, searchable in one place.
        </p>
        <div className="relative mt-4">
          <svg viewBox="0 0 24 24" className="pointer-events-none absolute top-1/2 left-3 size-5 -translate-y-1/2 text-stone-400" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
            <circle cx="11" cy="11" r="7" />
            <path d="m20 20-3.5-3.5" />
          </svg>
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder='Try "machine learning python", "robotics", "FPGA"…'
            aria-label="Search projects"
            autoFocus
            className="w-full rounded-xl border border-stone-300 bg-white py-3 pr-4 pl-11 text-base shadow-sm placeholder:text-stone-400 focus:border-accent-500 focus:outline-none dark:border-stone-700 dark:bg-stone-900"
          />
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-[16rem_1fr]">
        <aside className="min-w-0">
          <details className="rounded-xl border border-stone-200 bg-white px-4 lg:hidden dark:border-stone-800 dark:bg-stone-900">
            <summary className="cursor-pointer py-3 text-sm font-semibold">
              Filters{active > 0 && ` (${active})`}
            </summary>
            {facetPanel}
          </details>
          <div className="hidden lg:block">{facetPanel}</div>
        </aside>

        <section aria-live="polite" className="min-w-0">
          <div className="mb-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-stone-600 dark:text-stone-400">
            <span>
              <strong className="text-stone-900 dark:text-white">{results.length}</strong>{" "}
              {results.length === 1 ? "project" : "projects"}
            </span>
            {pastHidden > 0 && <span>· {pastHidden} from past semesters hidden</span>}
            {(active > 0 || filters.q) && (
              <button
                type="button"
                onClick={() => {
                  setQuery("");
                  update(EMPTY_FILTERS);
                }}
                className="font-medium text-accent-700 hover:underline dark:text-accent-400"
              >
                Clear all
              </button>
            )}
          </div>

          {results.length === 0 ? (
            <p className="rounded-xl border border-dashed border-stone-300 p-8 text-center text-stone-500 dark:border-stone-700">
              No project matches. Try fewer filters or other words.
            </p>
          ) : (
            <ul className="space-y-3">
              {results.slice(0, shown).map((p) => (
                <li key={p.id}>
                  <ProjectCard project={p} past={now ? isPastPeriod(p.period, now) : false} />
                </li>
              ))}
            </ul>
          )}

          {shown < results.length && (
            <button
              type="button"
              onClick={() => setShown(shown + PAGE_SIZE)}
              className="mt-4 w-full rounded-xl border border-stone-300 bg-white py-2.5 text-sm font-medium hover:bg-stone-100 dark:border-stone-700 dark:bg-stone-900 dark:hover:bg-stone-800"
            >
              Show more ({results.length - shown} left)
            </button>
          )}
        </section>
      </div>
    </div>
  );
}
