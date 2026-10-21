// Builds the cards into the integration, with their fonts. `--demo` builds the demo page.
import { build } from "esbuild";
import { copyFile, mkdir, writeFile } from "node:fs/promises";

// `--artifact <dir>` builds the demo with Lit left external, for a page that loads Lit from a CDN.
const artifactAt = process.argv.indexOf("--artifact");
const artifact = artifactAt > 0 ? process.argv[artifactAt + 1] : undefined;
const demo = process.argv.includes("--demo") || artifact !== undefined;
const out = artifact ?? (demo ? "demo/dist" : "../custom_components/gac_connect/frontend");
const fonts = [
  ["barlow-condensed", [500, 600, 700]],
  ["barlow", [400, 500]],
];

await mkdir(`${out}/fonts`, { recursive: true });
for (const [family, weights] of artifact ? [] : fonts) {
  for (const weight of weights) {
    for (const subset of ["latin", "latin-ext"]) {
      const name = `${family}-${subset}-${weight}-normal.woff2`;
      await copyFile(`node_modules/@fontsource/${family}/files/${name}`, `${out}/fonts/${name}`);
    }
  }
}
if (!artifact) await copyFile("node_modules/@fontsource/barlow/LICENSE", `${out}/fonts/OFL.txt`);

const options = {
  bundle: true,
  format: "esm",
  target: "es2021",
  minify: !demo,
  external: artifact ? ["lit"] : [],
  legalComments: "eof",
  logLevel: "warning",
};
if (demo) {
  await build({ ...options, entryPoints: ["demo/demo.ts"], outfile: `${out}/demo.js` });
  if (!artifact) await copyFile("demo/index.html", `${out}/index.html`);
} else {
  // Home Assistant loads the small loader on every page; the loader loads the cards once HA has booted.
  await build({ ...options, entryPoints: ["src/loader.ts"], outfile: `${out}/gac-connect-cards.js` });
  await build({ ...options, entryPoints: ["src/index.ts"], outfile: `${out}/gac-connect-cards-main.js` });
  await writeFile(`${out}/README.md`,
    "Built from `frontend/` by `npm run build`; do not edit. Fonts: Barlow and Barlow Condensed, SIL OFL 1.1 (fonts/OFL.txt).\n");
}
