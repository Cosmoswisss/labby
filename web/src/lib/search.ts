// Full-text search over the projects, in the browser (MiniSearch).

import MiniSearch from "minisearch";
import type { SearchProject } from "./types";

export function buildIndex(projects: SearchProject[]): MiniSearch<SearchProject> {
  const index = new MiniSearch<SearchProject>({
    fields: ["title", "summary", "domainsText", "skillsText", "supervisorsText", "labsText"],
    storeFields: ["id"],
    extractField: (doc, field) => {
      switch (field) {
        case "domainsText":
          return doc.domains.join(" ");
        case "skillsText":
          return doc.skills.join(" ");
        case "supervisorsText":
          return doc.supervisors.join(" ");
        case "labsText":
          return doc.labs.map((l) => l.acronym).join(" ");
        default:
          return (doc as unknown as Record<string, string>)[field];
      }
    },
    searchOptions: {
      boost: { title: 3, domainsText: 2, skillsText: 2, labsText: 2 },
      prefix: true,
      fuzzy: 0.2,
      combineWith: "AND",
    },
  });
  index.addAll(projects);
  return index;
}

/** Ids matching the query, best first; null when the query is empty (= no text filter). */
export function searchIds(index: MiniSearch<SearchProject>, query: string): string[] | null {
  const q = query.trim();
  if (!q) return null;
  return index.search(q).map((r) => String(r.id));
}
