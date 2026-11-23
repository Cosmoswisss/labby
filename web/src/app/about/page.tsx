import type { Metadata } from "next";
import { SITE } from "@/lib/site";

export const metadata: Metadata = { title: "About" };

const correctionBody =
  "Lab / page concerned:\nLabby page (if any):\n\nWhat should be corrected or removed?\n";

export default function AboutPage() {
  return (
    <div className="mx-auto max-w-3xl space-y-8 leading-relaxed">
      <section>
        <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">About Labby</h1>
        <p className="mt-3 text-stone-700 dark:text-stone-300">
          Every semester, EPFL students look for semester projects and master theses in labs.
          Each lab publishes its offers on its own website, in its own format. Labby gathers
          them in one place so you can search and filter across labs, including labs you did
          not know about.
        </p>
        <p className="mt-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-200">
          Labby is an unofficial student project, not affiliated with or endorsed by EPFL.
          Information may be incomplete or outdated: always check the lab&apos;s page, which is the
          reference, before applying.
        </p>
      </section>

      <section>
        <h2 className="text-xl font-semibold">How it works</h2>
        <ol className="mt-3 list-decimal space-y-2 pl-5 text-stone-700 dark:text-stone-300">
          <li>
            A crawler visits the public student-project page of each lab (and the project pages
            it links to), respecting robots.txt and at most about one request per second per
            site. Pages behind a login are never accessed.
          </li>
          <li>
            An AI model reads the text of each new or changed page and extracts the open projects
            (title, summary, level, supervisors, skills…). Completed or assigned projects are
            ignored and students&apos; names are never stored.
          </li>
          <li>
            The extraction is checked against pages annotated by hand. It is accurate but not
            perfect: a project may be missing, outdated or slightly wrong.
          </li>
          <li>
            Every project links back to the lab&apos;s page and shows when it was last checked.
          </li>
        </ol>
        <p className="mt-3 text-sm text-stone-600 dark:text-stone-400">
          Current coverage: labs listed for the IC master programmes (IC labs and accredited labs
          of other schools). Other schools will follow. The code is open source on{" "}
          <a href={SITE.repoUrl} className="underline">GitHub</a>.
        </p>
      </section>

      <section>
        <h2 className="text-xl font-semibold">For labs: corrections and removal</h2>
        <p className="mt-3 text-stone-700 dark:text-stone-300">
          If a project is outdated, wrong or should not be listed, or if you prefer your lab not
          to appear on Labby, open an issue and it will be handled quickly. You can also update
          your own page: Labby re-reads it automatically on its next update.
        </p>
        <a
          href={SITE.issueUrl("Correction / removal request", correctionBody)}
          className="mt-4 inline-flex rounded-lg bg-accent-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-accent-700"
        >
          Request a correction or removal
        </a>
        <p className="mt-2 text-xs text-stone-500 dark:text-stone-400">Requires a GitHub account.</p>
      </section>
    </div>
  );
}
