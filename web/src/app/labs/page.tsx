import type { Metadata } from "next";
import Link from "next/link";
import { Badge, type BadgeTone } from "@/components/ui/Badge";
import { Icon } from "@/components/ui/Icon";
import { Container, PageHeader } from "@/components/ui/Layout";
import { getLabs } from "@/lib/data";
import type { Lab, LabStatus } from "@/lib/types";

export const metadata: Metadata = { title: "Labs" };

const FACULTY_NAMES: Record<string, string> = {
  IC: "Computer and Communication Sciences",
  STI: "Engineering",
  SB: "Basic Sciences",
  SV: "Life Sciences",
  ENAC: "Architecture, Civil and Environmental Engineering",
  CDM: "Management of Technology",
  CDH: "Humanities",
  ENT: "Centers and other units",
  OTHER: "Other",
};

const STATUS_INFO: Partial<Record<LabStatus, { label: string; tone: BadgeTone }>> = {
  none: { label: "No public list", tone: "neutral" },
  restricted: { label: "EPFL login required", tone: "warning" },
  js_rendered: { label: "Not indexed yet", tone: "neutral" },
  auto: { label: "Coming soon", tone: "neutral" },
  blocked: { label: "Not indexable", tone: "neutral" },
  error: { label: "Page unreachable", tone: "warning" },
};

function LabCard({ lab }: { lab: Lab }) {
  const info = STATUS_INFO[lab.status];
  return (
    <li
      id={lab.id}
      className="flex scroll-mt-24 flex-col rounded-xl border border-border bg-surface p-5 shadow-soft transition-all duration-200 hover:border-border-strong hover:shadow-lift"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="font-semibold tracking-tight">{lab.acronym}</h3>
          <p className="mt-0.5 text-sm leading-snug text-fg-muted">{lab.name}</p>
        </div>
        {lab.project_count > 0 && (
          <Badge tone="primary">
            {lab.project_count} {lab.project_count === 1 ? "project" : "projects"}
          </Badge>
        )}
      </div>
      {lab.heads.length > 0 && (
        <p className="mt-3 flex items-center gap-1.5 text-sm text-fg-subtle">
          <Icon name="user" className="size-3.5" />
          <span className="truncate">{lab.heads.join(" · ")}</span>
        </p>
      )}
      <div className="mt-auto flex flex-wrap items-center gap-x-4 gap-y-2 pt-4 text-sm">
        {info && <Badge tone={info.tone}>{info.label}</Badge>}
        {lab.project_count > 0 ? (
          <Link
            href={`/?lab=${lab.id}`}
            className="inline-flex items-center gap-1 font-medium text-primary-text underline-offset-2 hover:underline"
          >
            See projects <Icon name="arrowRight" className="size-3.5" />
          </Link>
        ) : (
          lab.status === "ok" && <span className="text-fg-subtle">No open project found</span>
        )}
        {lab.projects_url && (
          <a
            href={lab.projects_url}
            target="_blank"
            rel="noopener noreferrer"
            className="ml-auto inline-flex items-center gap-1 text-fg-muted transition-colors duration-200 hover:text-fg"
          >
            Lab page <Icon name="external" className="size-3.5" />
            <span className="sr-only">for {lab.acronym} (opens in a new tab)</span>
          </a>
        )}
      </div>
    </li>
  );
}

export default function LabsPage() {
  const labs = getLabs();
  const byFaculty = new Map<string, Lab[]>();
  for (const lab of labs) byFaculty.set(lab.faculty, [...(byFaculty.get(lab.faculty) ?? []), lab]);
  const faculties = Object.keys(FACULTY_NAMES).filter((f) => byFaculty.has(f));
  const indexed = labs.filter((l) => l.status === "ok").length;
  const withProjects = labs.filter((l) => l.project_count > 0).length;

  const stats = [
    { value: labs.length, label: "labs and units listed" },
    { value: indexed, label: "with a public project page" },
    { value: withProjects, label: "with open projects now" },
  ];

  return (
    <Container>
      <PageHeader
        eyebrow="Coverage"
        title="Labs"
        description="All EPFL labs from the official list. IC and STI labs are indexed; the other schools are being added. For labs without a public project list, Labby links to their page so you can contact them directly."
      >
        <dl className="mt-8 grid max-w-2xl grid-cols-3 gap-4">
          {stats.map((s) => (
            <div key={s.label} className="rounded-xl border border-border bg-surface p-4 shadow-soft">
              <dt className="text-sm leading-snug text-fg-subtle">{s.label}</dt>
              <dd className="mt-1 text-2xl font-semibold tracking-tight">{s.value}</dd>
            </div>
          ))}
        </dl>
      </PageHeader>

      <nav aria-label="Schools" className="sticky top-16 z-30 -mx-5 mb-8 border-b border-border bg-bg/85 px-5 py-3 backdrop-blur-lg sm:-mx-8 sm:px-8">
        <ul className="flex gap-2 overflow-x-auto [scrollbar-width:none]">
          {faculties.map((f) => (
            <li key={f}>
              <a
                href={`#school-${f}`}
                className="block rounded-full border border-border bg-surface px-3 py-1 text-sm whitespace-nowrap text-fg-muted transition-all duration-200 hover:border-primary hover:bg-primary-soft hover:text-primary-soft-fg"
              >
                {f} <span className="text-fg-subtle">{byFaculty.get(f)!.length}</span>
              </a>
            </li>
          ))}
        </ul>
      </nav>

      <div className="space-y-14">
        {faculties.map((faculty) => (
          <section key={faculty} id={`school-${faculty}`} aria-labelledby={`h-${faculty}`} className="scroll-mt-32">
            <h2 id={`h-${faculty}`} className="text-xl font-semibold tracking-tight">
              {FACULTY_NAMES[faculty]}{" "}
              <span className="font-normal text-fg-subtle">({faculty})</span>
            </h2>
            <ul className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {byFaculty
                .get(faculty)!
                .sort((a, b) => b.project_count - a.project_count || a.acronym.localeCompare(b.acronym))
                .map((lab) => (
                  <LabCard key={lab.id} lab={lab} />
                ))}
            </ul>
          </section>
        ))}
      </div>
    </Container>
  );
}
