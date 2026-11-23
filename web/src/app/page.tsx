import { Suspense } from "react";
import { SearchApp } from "@/components/SearchApp";
import { getLabs, getSearchProjects } from "@/lib/data";

export default function Home() {
  const projects = getSearchProjects();
  const labNames = Object.fromEntries(
    getLabs()
      .filter((lab) => lab.project_count > 0)
      .map((lab) => [lab.id, `${lab.acronym} — ${lab.name}`]),
  );
  return (
    // useSearchParams() reads the URL in the browser: the Suspense boundary lets the
    // rest of the page be prerendered as static HTML.
    <Suspense fallback={<p className="text-stone-500">Loading projects…</p>}>
      <SearchApp projects={projects} labNames={labNames} />
    </Suspense>
  );
}
