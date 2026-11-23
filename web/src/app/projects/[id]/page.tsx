import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import type { ReactNode } from "react";
import { BackLink } from "@/components/BackLink";
import { Badge, StatusBadge } from "@/components/ui/Badge";
import { ButtonLink } from "@/components/ui/Button";
import { Icon, type IconName } from "@/components/ui/Icon";
import { Card, Container } from "@/components/ui/Layout";
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

function Fact({ icon, label, children }: { icon: IconName; label: string; children: ReactNode }) {
  return (
    <div className="flex gap-3 py-3.5">
      <Icon name={icon} className="mt-0.5 size-[18px] text-fg-subtle" />
      <div className="min-w-0">
        <dt className="text-sm text-fg-subtle">{label}</dt>
        <dd className="mt-0.5 font-medium text-fg">{children}</dd>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="mt-10">
      <h2 className="text-sm font-semibold tracking-wide text-fg-subtle uppercase">{title}</h2>
      <div className="mt-3">{children}</div>
    </section>
  );
}

export default async function ProjectPage({ params }: PageProps<"/projects/[id]">) {
  const { id } = await params;
  const project = getProject(id);
  if (!project) notFound();
  const labs = project.lab_ids.map((labId) => getLab(labId)).filter((l) => !!l);

  const issueBody = `Project: ${project.title}\nLabby page: /projects/${project.id}/\nSource: ${project.description_url}\n\nWhat is wrong (outdated, taken, wrong information, removal request…)?\n`;

  return (
    <Container className="pt-8 pb-4 sm:pt-10">
      <BackLink />

      <div className="mt-6 grid gap-10 lg:grid-cols-[minmax(0,1fr)_22rem] lg:gap-14">
        <article className="min-w-0">
          <p className="text-sm font-semibold text-primary-text">
            {labs.map((lab) => `${lab.acronym} — ${lab.name}`).join(" · ")}
          </p>
          <h1 className="mt-3 text-3xl leading-tight font-semibold tracking-tight text-balance sm:text-4xl">
            {project.title}
          </h1>
          <div className="mt-5 flex flex-wrap gap-2">
            <StatusBadge status={project.status} />
            {project.project_types.map((t) => (
              <Badge key={t} tone="primary">
                {PROJECT_TYPE_LABELS[t]}
              </Badge>
            ))}
          </div>

          {project.summary && (
            <p className="mt-8 text-lg leading-relaxed text-pretty text-fg-muted sm:text-xl sm:leading-relaxed">
              {project.summary}
            </p>
          )}

          {project.domains.length > 0 && (
            <Section title="Domains">
              <div className="flex flex-wrap gap-2">
                {project.domains.map((d) => (
                  <Link
                    key={d}
                    href={`/?domain=${encodeURIComponent(d.toLowerCase())}`}
                    className="rounded-full border border-border bg-surface px-3 py-1 text-sm text-fg-muted transition-all duration-200 hover:border-primary hover:bg-primary-soft hover:text-primary-soft-fg"
                  >
                    {d}
                  </Link>
                ))}
              </div>
            </Section>
          )}

          {project.skills.length > 0 && (
            <Section title="Skills">
              <ul className="flex flex-wrap gap-2">
                {project.skills.map((s) => (
                  <li key={s}>
                    <Badge>{s}</Badge>
                  </li>
                ))}
              </ul>
            </Section>
          )}

          <aside className="mt-12 flex gap-3 rounded-xl border border-border bg-surface-muted p-5 text-sm leading-relaxed text-fg-muted">
            <Icon name="info" className="mt-0.5 size-[18px] text-fg-subtle" />
            <p>
              This summary was extracted automatically from the lab&apos;s public page and may be
              incomplete or outdated. Something wrong?{" "}
              <a
                href={SITE.issueUrl(`Correction: ${project.title}`, issueBody)}
                className="font-medium text-primary-text underline underline-offset-2"
              >
                Report it
              </a>
              .
            </p>
          </aside>
        </article>

        <div className="lg:pt-1">
          <Card as="aside" className="p-6 lg:sticky lg:top-24">
            <ButtonLink href={project.description_url} external size="lg" className="w-full">
              Read &amp; apply on the lab&apos;s page
              <Icon name="external" className="size-4" />
            </ButtonLink>
            <p className="mt-3 text-center text-xs text-fg-subtle">
              The lab&apos;s page is the reference for details and deadlines.
            </p>

            <dl className="mt-5 divide-y divide-border border-t border-border">
              <Fact icon="user" label="Supervisors">
                {project.supervisors.length ? project.supervisors.join(", ") : "Not stated"}
              </Fact>
              <Fact icon="beaker" label="Lab">
                {labs.map((lab) => (
                  <Link
                    key={lab.id}
                    href={`/?lab=${lab.id}`}
                    className="mr-2 text-primary-text underline-offset-2 hover:underline"
                  >
                    {lab.acronym} <span className="font-normal text-fg-subtle">({lab.faculty})</span>
                  </Link>
                ))}
              </Fact>
              {project.academic_period && (
                <Fact icon="calendar" label="Semester">
                  {project.academic_period}
                </Fact>
              )}
              <Fact icon="globe" label="Language">
                {LANGUAGE_LABELS[project.language]}
              </Fact>
              <Fact icon="clock" label="Last checked">
                {formatDate(project.last_seen_at)}
                <span className="block text-sm font-normal text-fg-subtle">
                  First seen {formatDate(project.first_seen_at)}
                  {project.page_updated_at &&
                    ` · page updated ${formatDate(project.page_updated_at)}`}
                </span>
              </Fact>
            </dl>
          </Card>
        </div>
      </div>
    </Container>
  );
}
