import { Suspense } from "react";
import { SearchApp } from "@/components/SearchApp";
import { HeroShell, SearchBox } from "@/components/search/SearchHero";
import { Container } from "@/components/ui/Layout";
import { ProjectCardSkeleton, Skeleton } from "@/components/ui/States";
import { getLabs, getSearchProjects } from "@/lib/data";

/** Static placeholder shown until the search app reads the URL in the browser. */
function SearchSkeleton({ subtitle }: { subtitle: string }) {
  return (
    <Container>
      <HeroShell subtitle={subtitle}>
        <SearchBox value="" disabled />
      </HeroShell>
      <div className="grid gap-10 lg:grid-cols-[16.5rem_minmax(0,1fr)]" aria-busy="true">
        <div className="hidden space-y-3 lg:block">
          {Array.from({ length: 8 }, (_, i) => (
            <Skeleton key={i} className="h-5 w-full" />
          ))}
        </div>
        <div className="space-y-4">
          <Skeleton className="mb-5 h-7 w-40" />
          <span className="sr-only">Loading projects…</span>
          {Array.from({ length: 4 }, (_, i) => (
            <ProjectCardSkeleton key={i} />
          ))}
        </div>
      </div>
    </Container>
  );
}

export default function Home() {
  const projects = getSearchProjects();
  const labNames = Object.fromEntries(
    getLabs()
      .filter((lab) => lab.project_count > 0)
      .map((lab) => [lab.id, `${lab.acronym} — ${lab.name}`]),
  );
  const subtitle = `${projects.length} projects · ${Object.keys(labNames).length} labs · updated weekly`;
  return (
    // useSearchParams() reads the URL in the browser: the Suspense boundary lets the
    // rest of the page be prerendered, with skeletons in place of the results.
    <Suspense fallback={<SearchSkeleton subtitle={subtitle} />}>
      <SearchApp projects={projects} labNames={labNames} />
    </Suspense>
  );
}
