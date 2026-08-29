import { cp, mkdir, rm } from "node:fs/promises";
import { spawn } from "node:child_process";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const dist = resolve(root, "dist");

await rm(dist, { recursive: true, force: true });
await mkdir(dist, { recursive: true });
await cp(resolve(root, "site"), dist, { recursive: true });
await new Promise((resolveBuild, rejectBuild) => {
  const child = spawn(process.execPath, ["node_modules/vite/bin/vite.js", "build", "--config", "vite.config.mjs", "--configLoader", "native"], { cwd: root, stdio: "inherit" });
  child.once("error", rejectBuild);
  child.once("close", (code) => code === 0 ? resolveBuild() : rejectBuild(new Error(`Vite build exited with ${code}`)));
});
