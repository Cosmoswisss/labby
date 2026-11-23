"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useId, useMemo, useState } from "react";
import { useClientNow } from "@/lib/client";
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
import { ActiveFilters, type ListFacet } from "./search/ActiveFilters";
import { MobileFiltersDrawer } from "./search/MobileFiltersDrawer";
import { HeroShell, SearchBox, Suggestions } from "./search/SearchHero";
import { Button } from "./ui/Button";
import { Icon } from "./ui/Icon";
import { Container } from "./ui/Layout";
import { EmptyState } from "./ui/States";

const PAGE_SIZE = 30;
const FACULTY_ORDER = ["IC", "STI", "SB", "SV", "ENAC", "CDM", "CDH", "ENT", "OTHER"];
const TYPE_ORDER = ["semester_bachelor", "semester_master", "master_thesis", "other"];
const STATUS_ORDER = ["available", "reserved", "unknown"];
const LANGUAGE_ORDER = ["EN", "FR", "unknown"];

/** Fixed order for short facets, so options never jump under the cursor. */
function byOrder(order: string[]) {
  return (a: FacetOption, b: FacetOption) => order.indexOf(a.value) - order.indexOf(b.value);
}

/** "Include past semesters" switch; rendered in both the sidebar and the mobile drawer. */
function PastToggle({ checked, onChange }: { checked: boolean; onChange: () => void }) {
  const id = useId();
  return (
    <div className="py-5">
      <label
        htmlFor={id}
        className="flex cursor-pointer items-start gap-3 rounded-lg px-2 py-1.5 text-sm transition-colors duration-200 hover:bg-surface-muted"
      >
        <input
          id={id}
          type="checkbox"
          checked={checked}
          onChange={onChange}
          className="mt-0.5 size-4 shrink-0 cursor-pointer accent-[var(--primary)]"
        />
        <span>
          <span className="font-medium text-fg">Include past semesters</span>
          <span className="mt-0.5 block text-fg-subtle">Offers listed for a semester that is over</span>
        </span>
      </label>
    </div>
  );
}

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
  const filters = useMemo(
    () => parseFilters(new URLSearchParams(searchParams.toString())),
    [searchParams],
  );

  // The text box updates instantly; the URL (and the results) follow after a short pause.
  const [query, setQuery] = useState(filters.q);
  const [shown, setShown] = useState(PAGE_SIZE);
  const [drawerOpen, setDrawerOpen] = useState(false);
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
  function options(
    key: ListFacet,
    pick: (p: SearchProject) => string[],
    label: (v: string) => string,
  ): FacetOption[] {
    const base = applyFilters(textMatches, { ...filters, [key]: [] }, reference);
    return facetCounts(base, pick).map((c) => ({ ...c, label: label(c.value) }));
  }

  function toggle(key: ListFacet, value: string) {
    update({ ...filters, [key]: toggleValue(filters[key] as string[], value) });
  }

  const togglePast = () => update({ ...filters, includePast: !filters.includePast });
  const clearAll = () => {
    setQuery("");
    update(EMPTY_FILTERS);
  };
  const closeDrawer = useCallback(() => setDrawerOpen(false), []);

  const popularDomains = useMemo(
    () => facetCounts(projects, (p) => p.domains).slice(0, 6).map((c) => c.value),
    [projects],
  );

  const active = activeFilterCount(filters);
  const pastHidden = useMemo(
    () =>
      filters.includePast || !now
        ? 0
        : applyFilters(textMatches, { ...filters, includePast: true }, now).length -
          results.length,
    [filters, textMatches, results.length, now],
  );

  const facetPanel = (
    <div>
      <FacetGroup
        title="Project type"
        options={options("types", (p) => p.types, (v) => PROJECT_TYPE_LABELS[v as ProjectType]).sort(byOrder(TYPE_ORDER))}
        selected={filters.types}
        onToggle={(v) => toggle("types", v)}
      />
      <FacetGroup
        title="Faculty"
        options={options("faculties", (p) => p.faculties, (v) => v).sort(byOrder(FACULTY_ORDER))}
        selected={filters.faculties}
        onToggle={(v) => toggle("faculties", v)}
      />
      <FacetGroup
        title="Domain"
        options={options("domains", (p) => p.domains, (v) => v)}
        selected={filters.domains}
        onToggle={(v) => toggle("domains", v)}
        searchable
      />
      <FacetGroup
        title="Skills"
        options={options("skills", (p) => p.skills, (v) => v)}
        selected={filters.skills}
        onToggle={(v) => toggle("skills", v)}
        searchable
      />
      <FacetGroup
        title="Lab"
        options={options("labs", (p) => p.labs.map((l) => l.id), (v) => labNames[v] ?? v)}
        selected={filters.labs}
        onToggle={(v) => toggle("labs", v)}
        searchable
      />
      <FacetGroup
        title="Status"
        options={options("statuses", (p) => [p.status], (v) => STATUS_LABELS[v as ProjectStatus]).sort(byOrder(STATUS_ORDER))}
        selected={filters.statuses}
        onToggle={(v) => toggle("statuses", v)}
      />
      <FacetGroup
        title="Language"
        options={options("languages", (p) => [p.language], (v) => LANGUAGE_LABELS[v as Language]).sort(byOrder(LANGUAGE_ORDER))}
        selected={filters.languages}
        onToggle={(v) => toggle("languages", v)}
      />
      <PastToggle checked={filters.includePast} onChange={togglePast} />
    </div>
  );

  return (
    <Container>
      <HeroShell
        subtitle={`${projects.length} projects · ${Object.keys(labNames).length} labs · updated weekly`}
      >
        <SearchBox value={query} onChange={setQuery} />
        <Suggestions
          items={popularDomains}
          onPick={(d) => update({ ...filters, domains: toggleValue(filters.domains, d) })}
        />
      </HeroShell>

      <div className="grid gap-10 lg:grid-cols-[16.5rem_minmax(0,1fr)]">
        <aside aria-label="Filters" className="hidden lg:block">
          <div className="sticky top-24 -mt-5 max-h-[calc(100vh-7rem)] overflow-y-auto pr-3 [scrollbar-width:thin]">
            {facetPanel}
          </div>
        </aside>

        <section aria-labelledby="results-heading" className="min-w-0">
          <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 id="results-heading" className="text-xl font-semibold tracking-tight">
                {results.length} {results.length === 1 ? "project" : "projects"}
              </h2>
              {pastHidden > 0 && (
                <p className="mt-0.5 text-sm text-fg-subtle">
                  {pastHidden} from past semesters hidden ·{" "}
                  <button
                    type="button"
                    onClick={togglePast}
                    className="font-medium text-primary-text underline-offset-2 hover:underline"
                  >
                    show them
                  </button>
                </p>
              )}
            </div>
            <Button
              variant="secondary"
              className="lg:hidden"
              onClick={() => setDrawerOpen(true)}
              aria-haspopup="dialog"
            >
              <Icon name="filter" className="size-4" />
              Filters
              {active > 0 && (
                <span className="rounded-full bg-primary px-1.5 text-xs leading-5 text-primary-fg">
                  {active}
                </span>
              )}
            </Button>
          </div>

          <ActiveFilters
            filters={filters}
            labNames={labNames}
            onRemove={toggle}
            onTogglePast={togglePast}
            onClearAll={clearAll}
          />

          {results.length === 0 ? (
            <EmptyState
              title="No project matches your search"
              description="Try fewer filters, other keywords, or include past semesters."
              action={
                <Button variant="secondary" onClick={clearAll}>
                  Clear search and filters
                </Button>
              }
            />
          ) : (
            <ul className="space-y-4">
              {results.slice(0, shown).map((p) => (
                <li key={p.id}>
                  <ProjectCard project={p} past={now ? isPastPeriod(p.period, now) : false} />
                </li>
              ))}
            </ul>
          )}

          {shown < results.length && (
            <div className="mt-8 flex flex-col items-center gap-2">
              <Button variant="secondary" size="lg" onClick={() => setShown(shown + PAGE_SIZE)}>
                Show more projects
              </Button>
              <p className="text-sm text-fg-subtle">
                Showing {shown} of {results.length}
              </p>
            </div>
          )}
        </section>
      </div>

      <MobileFiltersDrawer open={drawerOpen} onClose={closeDrawer} resultCount={results.length}>
        {facetPanel}
      </MobileFiltersDrawer>
    </Container>
  );
}
