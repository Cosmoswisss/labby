import type { Metadata } from "next";
import { ButtonLink } from "@/components/ui/Button";
import { Icon, type IconName } from "@/components/ui/Icon";
import { Container, PageHeader } from "@/components/ui/Layout";
import { SITE } from "@/lib/site";

export const metadata: Metadata = { title: "About" };

const correctionBody =
  "Lab / page concerned:\nLabby page (if any):\n\nWhat should be corrected or removed?\n";

const STEPS: { icon: IconName; title: string; text: string }[] = [
  {
    icon: "globe",
    title: "Crawl public lab pages",
    text: "Each lab's public student-project page (and the project pages it links to) is visited weekly, respecting robots.txt and about one request per second per site. Pages behind a login are never accessed.",
  },
  {
    icon: "sparkles",
    title: "Extract the open projects",
    text: "An AI model reads each new or changed page and extracts the open projects: title, summary, level, supervisors, skills. Completed or assigned projects are ignored and students' names are never stored.",
  },
  {
    icon: "check",
    title: "Check the quality",
    text: "The extraction is measured against pages annotated by hand. It is accurate but not perfect: a project may be missing, outdated or slightly wrong.",
  },
  {
    icon: "external",
    title: "Send you to the source",
    text: "Every project links back to the lab's page, which stays the reference, and shows when it was last checked.",
  },
];

export default function AboutPage() {
  return (
    <Container>
      <PageHeader
        eyebrow="About"
        title="All EPFL lab projects, in one search"
        description="Every semester, EPFL students look for semester projects and master theses in labs. Each lab publishes its offers on its own website, in its own format. Labby gathers them in one place so you can search and filter across labs, including labs you did not know about."
      />

      <div className="flex max-w-3xl gap-3 rounded-xl border border-warning-fg/25 bg-warning-soft p-5 text-warning-fg">
        <Icon name="info" className="mt-0.5 size-5" />
        <p className="leading-relaxed">
          <strong className="font-semibold">Unofficial student project</strong>, not affiliated
          with or endorsed by EPFL. Information may be incomplete or outdated: always check the
          lab&apos;s page, which is the reference, before applying.
        </p>
      </div>

      <section aria-labelledby="how" className="mt-16">
        <h2 id="how" className="text-2xl font-semibold tracking-tight">
          How it works
        </h2>
        <ol className="mt-6 grid gap-4 sm:grid-cols-2">
          {STEPS.map((step, i) => (
            <li key={step.title} className="rounded-xl border border-border bg-surface p-6 shadow-soft">
              <div className="flex items-center gap-3">
                <span className="flex size-10 items-center justify-center rounded-[10px] bg-primary-soft text-primary-soft-fg">
                  <Icon name={step.icon} />
                </span>
                <span className="text-sm font-semibold text-fg-subtle">Step {i + 1}</span>
              </div>
              <h3 className="mt-4 text-lg font-semibold tracking-tight">{step.title}</h3>
              <p className="mt-2 leading-relaxed text-fg-muted">{step.text}</p>
            </li>
          ))}
        </ol>
        <p className="mt-6 max-w-3xl text-fg-muted">
          Current coverage: labs listed for the IC master programmes (IC labs and accredited labs
          of other schools). Other schools will follow. The code is open source on{" "}
          <a href={SITE.repoUrl} className="font-medium text-primary-text underline underline-offset-2">
            GitHub
          </a>
          .
        </p>
      </section>

      <section
        id="corrections"
        aria-labelledby="corrections-title"
        className="mt-16 scroll-mt-24 rounded-2xl border border-border bg-surface p-8 shadow-soft sm:p-10"
      >
        <span className="flex size-11 items-center justify-center rounded-[10px] bg-primary-soft text-primary-soft-fg">
          <Icon name="flag" />
        </span>
        <h2 id="corrections-title" className="mt-5 text-2xl font-semibold tracking-tight">
          For labs: corrections and removal
        </h2>
        <p className="mt-3 max-w-2xl leading-relaxed text-fg-muted">
          If a project is outdated, wrong or should not be listed, or if you prefer your lab not to
          appear on Labby, open an issue and it will be handled quickly. You can also update your
          own page: Labby re-reads it automatically on its next weekly update.
        </p>
        <div className="mt-6 flex flex-wrap items-center gap-4">
          <ButtonLink href={SITE.issueUrl("Correction / removal request", correctionBody)} size="lg">
            <Icon name="github" className="size-4" />
            Request a correction or removal
          </ButtonLink>
          <span className="text-sm text-fg-subtle">Requires a GitHub account.</span>
        </div>
      </section>
    </Container>
  );
}
