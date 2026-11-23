export const SITE = {
  name: "Labby",
  tagline: "Student projects in EPFL labs, in one place",
  repoUrl: "https://github.com/Cosmoswisss/labby",
  /** Pre-filled GitHub issue for corrections / removal requests. */
  issueUrl(title: string, body: string): string {
    const params = new URLSearchParams({ title, body, labels: "data-correction" });
    return `https://github.com/Cosmoswisss/labby/issues/new?${params.toString()}`;
  },
};

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "unknown";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}
