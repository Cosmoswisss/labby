import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { BackLink } from "@/components/BackLink";
import { Badge, StatusBadge } from "@/components/Badges";
import { getLab, getProject, getProjects } from "@/lib/data";
import { SITE, formatDate } from "@/lib/site";
import { LANGUAGE_LABELS, PROJECT_TYPE_LABELS } from "@/lib/types";

// Static export: one HTML page per project, generated at build time.
export function generateStaticParams() {
  return getProjects().map((p) => ({ id: p.id }));
}

export async function generateMetadata({ params }: PageProps<"/projects/[id]">): Promise<Metadata> {
  const { id } = await params;
  const project = getProject(id);
  return project ? { title: project.title, description: project.summary } : {};
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid gap-1 py-3 sm:grid-cols-[10rem_1fr]">
      <dt className="text-sm font-medium text-stone-500 dark:text-stone-400">{label}</dt>
      <dd className="text-sm">{children}</dd>
    </div>
  );
}

export default async function ProjectPage({ params }: PageProps<"/projects/[id]">) {
  const { id } = await params;
  const project = getProject(id);
  if (!project) notFound();
  const labs = project.lab_ids.map((labId) => getLab(labId)).filter((l) => !!l);

  const issueBody = `Project: ${project.title}\nLabby page: /projects/${project.id}/\nSource: ${project.description_url}\n\nWhat is wrong (outdated, taken, wrong information, removal request…)?\n`;

  return (
    <article className="mx-auto max-w-3xl">
      <BackLink />

      <header className="mt-4">
        <p className="text-sm font-semibold text-accent-700 dark:text-accent-400">
          {labs.map((lab) => `${lab.acronym} — ${lab.name}`).join(" · ")}
        </p>
        <h1 className="mt-1 text-2xl leading-tight font-bold tracking-tight sm:text-3xl">
          {project.title}
        </h1>
        <div className="mt-3 flex flex-wrap gap-1.5">
          <StatusBadge status={project.status} />
          {project.project_types.map((t) => (
            <Badge key={t}>{PROJECT_TYPE_LABELS[t]}</Badge>
          ))}
          {project.academic_period && <Badge tone="muted">{project.academic_period}</Badge>}
        </div>
      </header>

      {project.summary && (
        <p className="mt-5 text-lg leading-relaxed text-stone-700 dark:text-stone-300">
          {project.summary}
        </p>
      )}

      <div className="mt-6 flex flex-wrap items-center gap-3">
        <a
          href={project.description_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 rounded-lg bg-accent-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-accent-700"
        >
          Read the full description on the lab&apos;s page ↗
        </a>
        <span className="text-xs text-stone-500 dark:text-stone-400">
          The lab&apos;s page is the reference (application, deadlines, details).
        </span>
      </div>

      <dl className="mt-8 divide-y divide-stone-200 rounded-xl border border-stone-200 bg-white px-4 dark:divide-stone-800 dark:border-stone-800 dark:bg-stone-900">
        <Row label="Supervisors">
          {project.supervisors.length ? project.supervisors.join(", ") : "Not stated on the page"}
        </Row>
        <Row label="Lab">
          {labs.map((lab) => (
            <span key={lab.id} className="mr-3 inline-block">
              <Link href={`/?lab=${lab.id}`} className="font-medium text-accent-700 hover:underline dark:text-accent-400">
                {lab.acronym}
              </Link>{" "}
              <span className="text-stone-500">({lab.faculty})</span>
            </span>
          ))}
        </Row>
        {project.domains.length > 0 && (
          <Row label="Domains">
            <div className="flex flex-wrap gap-1.5">
              {project.domains.map((d) => (
                <Link key={d} href={`/?domain=${encodeURIComponent(d.toLowerCase())}`}>
                  <Badge tone="muted">{d}</Badge>
                </Link>
              ))}
            </div>
          </Row>
        )}
        {project.skills.length > 0 && <Row label="Skills">{project.skills.join(", ")}</Row>}
        <Row label="Language">{LANGUAGE_LABELS[project.language]}</Row>
        {project.page_updated_at && (
          <Row label="Page updated">{formatDate(project.page_updated_at)} (as shown by the lab)</Row>
        )}
        <Row label="Last checked">
          {formatDate(project.last_seen_at)} · first seen {formatDate(project.first_seen_at)}
        </Row>
      </dl>

      <aside className="mt-6 rounded-xl bg-stone-100 p-4 text-sm text-stone-600 dark:bg-stone-900 dark:text-stone-400">
        This summary was extracted automatically from the lab&apos;s public page and may contain
        mistakes or be outdated. Something wrong?{" "}
        <a
          href={SITE.issueUrl(`Correction: ${project.title}`, issueBody)}
          className="font-medium text-accent-700 underline dark:text-accent-400"
        >
          Report it
        </a>
        .
      </aside>
    </article>
  );
}
