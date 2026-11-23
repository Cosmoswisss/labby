import type { Metadata } from "next";
import Link from "next/link";
import { ThemeToggle } from "@/components/ThemeToggle";
import { generatedAt } from "@/lib/data";
import { SITE, formatDate } from "@/lib/site";
import { THEME_SCRIPT } from "@/lib/theme-script";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: `${SITE.name} — ${SITE.tagline}`, template: `%s · ${SITE.name}` },
  description:
    "Unofficial search engine for semester, bachelor and master projects offered by EPFL labs.",
};

const NAV = [
  { href: "/", label: "Search" },
  { href: "/labs/", label: "Labs" },
  { href: "/about/", label: "About" },
];

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body className="flex min-h-screen flex-col">
        <header className="border-b border-stone-200 bg-white/80 backdrop-blur dark:border-stone-800 dark:bg-stone-900/80">
          <div className="mx-auto flex max-w-6xl items-center gap-6 px-4 py-3">
            <Link href="/" className="flex items-baseline gap-2">
              <span className="text-xl font-bold tracking-tight">
                Lab<span className="text-accent-600 dark:text-accent-400">by</span>
              </span>
              <span className="hidden text-sm text-stone-500 sm:inline dark:text-stone-400">
                {SITE.tagline}
              </span>
            </Link>
            <nav className="ml-auto flex items-center gap-1 text-sm">
              {NAV.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="rounded-md px-3 py-2 font-medium text-stone-600 hover:bg-stone-100 hover:text-stone-900 dark:text-stone-300 dark:hover:bg-stone-800 dark:hover:text-white"
                >
                  {item.label}
                </Link>
              ))}
              <ThemeToggle />
            </nav>
          </div>
        </header>

        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6">{children}</main>

        <footer className="border-t border-stone-200 bg-white text-sm text-stone-600 dark:border-stone-800 dark:bg-stone-900 dark:text-stone-400">
          <div className="mx-auto max-w-6xl space-y-2 px-4 py-6">
            <p className="font-medium text-stone-800 dark:text-stone-200">
              Unofficial student project, not affiliated with EPFL. Information may be
              incomplete or outdated: the lab&apos;s own page is the reference.
            </p>
            <p>
              Data extracted automatically from public lab pages · last update{" "}
              {formatDate(generatedAt)} ·{" "}
              <Link href="/about/" className="underline hover:text-stone-900 dark:hover:text-white">
                how it works &amp; corrections
              </Link>{" "}
              ·{" "}
              <a href={SITE.repoUrl} className="underline hover:text-stone-900 dark:hover:text-white">
                source code
              </a>
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
