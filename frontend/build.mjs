import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";

const base = process.env.API_BASE_URL?.trim();
const url = base ? new URL(base) : null;
if (url && (url.protocol !== "https:" || url.pathname !== "/" || url.search || url.hash || url.username || url.password)) {
  throw new Error("API_BASE_URL must be a bare HTTPS origin");
}
const output = new URL("dist/", import.meta.url);
mkdirSync(output, {recursive: true});
for (const file of ["index.html", "style.css", "app.js"]) {
  copyFileSync(new URL(file, import.meta.url), new URL(file, output));
}
writeFileSync(new URL("config.js", output), `globalThis.API_BASE_URL = ${JSON.stringify(url?.origin || "")}; globalThis.WONDER_DEPLOYED = true;\n`);