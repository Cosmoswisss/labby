import { describe, expect, it } from "vitest";
import {
  EMPTY_FILTERS,
  activeFilterCount,
  applyFilters,
  facetCounts,
  isPastPeriod,
  parseFilters,
  serializeFilters,
  toggleValue,
} from "./filters";
import { buildIndex, searchIds } from "./search";
import type { SearchProject } from "./types";

function project(over: Partial<SearchProject>): SearchProject {
  return {
    id: "x",
    title: "A project",
    summary: "",
    labs: [{ id: "ic-cvlab", acronym: "CVLAB" }],
    faculties: ["IC"],
    types: [],
    domains: [],
    topics: [],
    skills: [],
    language: "EN",
    supervisors: [],
    status: "available",
    period: null,
    lastSeen: null,
    ...over,
  };
}

const NOW = new Date(2026, 10, 23); // 23 Nov 2026

describe("URL state", () => {
  it("round-trips filters through the query string", () => {
    const filters = {
      ...EMPTY_FILTERS,
      q: "computer vision",
      types: ["master_thesis", "semester_master"] as const,
      faculties: ["IC"],
      includePast: true,
    };
    const qs = serializeFilters({ ...filters, types: [...filters.types] });
    expect(qs).toBe("q=computer+vision&type=master_thesis%2Csemester_master&faculty=IC&past=1");
    expect(parseFilters(new URLSearchParams(qs))).toEqual({ ...filters, types: [...filters.types] });
  });

  it("omits empty values", () => {
    expect(serializeFilters(EMPTY_FILTERS)).toBe("");
    expect(parseFilters(new URLSearchParams(""))).toEqual(EMPTY_FILTERS);
  });
});

describe("isPastPeriod", () => {
  it.each([
    ["Spring 2026", true],
    ["Fall 2025", true],
    ["Autumn 2026", false], // runs until January 2027
    ["Spring 2027", false],
    ["Spring Semester 2026-2027", false],
    ["2025-2026", true],
    ["2025", true],
    ["2026", false],
    [null, false],
    ["next semester", false],
  ])("%s -> %s", (period, expected) => {
    expect(isPastPeriod(period, NOW)).toBe(expected);
  });
});

describe("applyFilters", () => {
  const projects = [
    project({ id: "a", types: ["master_thesis"], faculties: ["IC"], period: "Spring 2027" }),
    project({ id: "b", types: ["semester_bachelor"], faculties: ["STI"], status: "reserved" }),
    project({ id: "c", types: ["master_thesis"], faculties: ["IC"], period: "Spring 2025" }),
  ];

  it("hides past-semester offers unless asked", () => {
    expect(applyFilters(projects, EMPTY_FILTERS, NOW).map((p) => p.id)).toEqual(["a", "b"]);
    const all = applyFilters(projects, { ...EMPTY_FILTERS, includePast: true }, NOW);
    expect(all.map((p) => p.id)).toEqual(["a", "b", "c"]);
  });

  it("combines facets with AND, values within a facet with OR", () => {
    const f = { ...EMPTY_FILTERS, types: ["master_thesis", "semester_bachelor"] as never[] };
    expect(applyFilters(projects, f, NOW).map((p) => p.id)).toEqual(["a", "b"]);
    const g = { ...f, faculties: ["STI"] };
    expect(applyFilters(projects, g, NOW).map((p) => p.id)).toEqual(["b"]);
  });

  it("filters by topic", () => {
    const withTopics = [
      project({ id: "t1", topics: ["Machine learning & AI"] }),
      project({ id: "t2", topics: ["Hardware & circuits"] }),
    ];
    const f = { ...EMPTY_FILTERS, topics: ["Hardware & circuits"] };
    expect(applyFilters(withTopics, f, NOW).map((p) => p.id)).toEqual(["t2"]);
    expect(serializeFilters(f)).toBe("topic=Hardware+%26+circuits");
    expect(parseFilters(new URLSearchParams("topic=Hardware+%26+circuits")).topics).toEqual([
      "Hardware & circuits",
    ]);
  });

  it("filters by status and lab", () => {
    const f = { ...EMPTY_FILTERS, statuses: ["reserved"] as never[] };
    expect(applyFilters(projects, f, NOW).map((p) => p.id)).toEqual(["b"]);
    expect(applyFilters(projects, { ...EMPTY_FILTERS, labs: ["ic-other"] }, NOW)).toEqual([]);
  });
});

describe("facets and helpers", () => {
  it("counts each value once per project, most frequent first", () => {
    const projects = [
      project({ domains: ["robotics", "robotics", "vision"] }),
      project({ domains: ["vision"] }),
    ];
    expect(facetCounts(projects, (p) => p.domains)).toEqual([
      { value: "vision", count: 2 },
      { value: "robotics", count: 1 },
    ]);
    expect(facetCounts(projects, (p) => p.domains, 2)).toEqual([{ value: "vision", count: 2 }]);
  });

  it("toggles values and counts active filters", () => {
    expect(toggleValue(["a"], "b")).toEqual(["a", "b"]);
    expect(toggleValue(["a", "b"], "a")).toEqual(["b"]);
    expect(activeFilterCount({ ...EMPTY_FILTERS, labs: ["x"], includePast: true })).toBe(2);
  });
});

describe("search", () => {
  const projects = [
    project({ id: "1", title: "Drone perception with deep learning", skills: ["PyTorch"] }),
    project({ id: "2", title: "FPGA compiler passes", skills: ["C++"], labs: [{ id: "ic-lap", acronym: "LAP" }] }),
  ];
  const index = buildIndex(projects);

  it("matches prefixes, skills, lab acronyms and typos", () => {
    expect(searchIds(index, "percep")).toEqual(["1"]);
    expect(searchIds(index, "pytorch")).toEqual(["1"]);
    expect(searchIds(index, "LAP")).toEqual(["2"]);
    expect(searchIds(index, "compilr")).toEqual(["2"]);
  });

  it("returns null for an empty query", () => {
    expect(searchIds(index, "  ")).toBeNull();
  });
});
