import Link from "next/link";
import { SITE, formatDate } from "@/lib/site";
import { Icon } from "./ui/Icon";

export function SiteFooter({ updatedAt }: { updatedAt: string }) {
  return (
    <footer className="mt-24 border-t border-border bg-surface">
      <div className="mx-auto grid w-full max-w-6xl gap-8 px-5 py-10 sm:px-8 md:grid-cols-[1.4fr_1fr]">
        <div>
          <p className="flex items-start gap-2.5 text-sm leading-relaxed font-medium text-fg">
            <Icon name="info" className="mt-0.5 size-4 text-primary-text" />
            <span>
              Unofficial student project, not affiliated with EPFL. Information may be incomplete
              or outdated: the lab&apos;s own page is the reference.
            </span>
          </p>
          <p className="mt-3 pl-6.5 text-sm text-fg-subtle">
            Data extracted automatically from public lab pages · updated {formatDate(updatedAt)}
          </p>
        </div>
        <nav aria-label="Footer" className="flex flex-wrap items-start gap-x-6 gap-y-2 text-sm md:justify-end">
          <Link href="/about/" className="text-fg-muted transition-colors duration-200 hover:text-fg">
            How it works
          </Link>
          <Link href="/about/#corrections" className="text-fg-muted transition-colors duration-200 hover:text-fg">
            Corrections &amp; removal
          </Link>
          <a
            href={SITE.repoUrl}
            className="inline-flex items-center gap-1.5 text-fg-muted transition-colors duration-200 hover:text-fg"
          >
            <Icon name="github" className="size-4" />
            Source code
          </a>
        </nav>
      </div>
    </footer>
  );
}
