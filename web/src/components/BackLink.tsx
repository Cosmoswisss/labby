"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

/** Goes back to the previous search (keeping its filters) when coming from this site. */
export function BackLink() {
  const router = useRouter();
  return (
    <Link
      href="/"
      onClick={(e) => {
        const fromSite = document.referrer.startsWith(window.location.origin);
        if (fromSite && window.history.length > 1) {
          e.preventDefault();
          router.back();
        }
      }}
      className="text-sm text-accent-700 hover:underline dark:text-accent-400"
    >
      ← Back to search
    </Link>
  );
}
