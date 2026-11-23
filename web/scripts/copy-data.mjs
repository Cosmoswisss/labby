// Copies the pipeline output (../data/*.json) into src/data/ before dev/build,
// so the app imports it like any module. src/data/ is gitignored.
import { copyFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const source = join(root, "..", "data");
const target = join(root, "src", "data");
mkdirSync(target, { recursive: true });
for (const name of ["projects.json", "labs.json"]) {
  const from = join(source, name);
  if (!existsSync(from)) {
    console.error(`Missing ${from}: run the pipeline export first.`);
    process.exit(1);
  }
  copyFileSync(from, join(target, name));
}
console.log("Copied data/projects.json and data/labs.json to src/data/");
