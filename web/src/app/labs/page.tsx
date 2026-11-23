import type { Metadata } from "next";
import Link from "next/link";
import { Badge } from "@/components/Badges";
import { getLabs } from "@/lib/data";
import type { Lab, LabStatus } from "@/lib/types";

export const metadata: Metadata = { title: "Labs" };

const FACULTY_NAMES: Record<string, string> = {
  IC: "Computer and Communication Sciences (IC)",
  STI: "Engineering (STI)",
  SB: "Basic Sciences (SB)",
  SV: "Life Sciences (SV)",
  ENAC: "Architecture, Civil and Environmental Engineering (ENAC)",
  CDM: "Management of Technology (CDM)",
  CDH: "Humanities (CDH)",
  ENT: "Centers and other units",
  OTHER: "Other",
};

const STATUS_INFO: Partial<Record<LabStatus, { label: string; tone: "amber" | "muted" }>> = {
  none: { label: "No public list", tone: "muted" },
  restricted: { label: "EPFL login required", tone: "amber" },
  js_rendered: { label: "Not indexed yet", tone: "muted" },
  blocked: { label: "Not indexable", tone: "muted" },
  error: { label: "Page unreachable", tone: "amber" },
};

function LabRow({ lab }: { lab: Lab }) {
  const info = STATUS_INFO[lab.status];
  return (
    <li id={lab.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 py-3">
      <div className="min-w-0 flex-1">
        <p className="font-medium">
          {lab.acronym} <span className="font-normal text-stone-500 dark:text-stone-400">— {lab.name}</span>
        </p>
        {lab.heads.length > 0 && (
          <p className="text-xs text-stone-500 dark:text-stone-400">{lab.heads.join(" · ")}</p>
        )}
      </div>
      <div className="flex items-center gap-3 text-sm">
        {info && <Badge tone={info.tone}>{info.label}</Badge>}
        {lab.project_count > 0 ? (
          <Link href={`/?lab=${lab.id}`} className="font-medium text-accent-700 hover:underline dark:text-accent-400">
            {lab.project_count} {lab.project_count === 1 ? "project" : "projects"}
          </Link>
        ) : lab.status === "ok" ? (
          <span className="text-stone-400">no open project found</span>
        ) : null}
        {lab.projects_url && (
          <a href={lab.projects_url} target="_blank" rel="noopener noreferrer" className="text-stone-500 underline hover:text-stone-900 dark:text-stone-400 dark:hover:text-white">
            lab page ↗
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

  return (
    <div className="mx-auto max-w-4xl">
      <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">Labs</h1>
      <p className="mt-2 text-stone-600 dark:text-stone-400">
        {labs.length} labs and units listed for IC students (IC labs and labs of other schools
        accredited by the IC sections). {indexed} have a public project page that Labby reads.
        For the others, Labby only links to the lab: check their page or contact them directly.
      </p>

      {faculties.map((faculty) => (
        <section key={faculty} className="mt-8">
          <h2 className="text-lg font-semibold">{FACULTY_NAMES[faculty]}</h2>
          <ul className="mt-2 divide-y divide-stone-200 rounded-xl border border-stone-200 bg-white px-4 dark:divide-stone-800 dark:border-stone-800 dark:bg-stone-900">
            {byFaculty
              .get(faculty)!
              .sort((a, b) => a.acronym.localeCompare(b.acronym))
              .map((lab) => (
                <LabRow key={lab.id} lab={lab} />
              ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
