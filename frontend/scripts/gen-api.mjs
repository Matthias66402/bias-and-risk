// Export the FastAPI OpenAPI schema (no server needed) and generate TS types from it.
import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";
import { resolve } from "node:path";

const backend = resolve(import.meta.dirname, "../../backend");
const py = process.platform === "win32" ? ".venv/Scripts/python.exe" : ".venv/bin/python";
const python = existsSync(resolve(backend, py)) ? resolve(backend, py) : "python";
const schema = resolve(import.meta.dirname, "../openapi.json");

execFileSync(python, ["scripts/export_openapi.py", schema], { cwd: backend, stdio: "inherit" });
execFileSync(process.execPath, [resolve(import.meta.dirname, "../node_modules/openapi-typescript/bin/cli.js"), schema, "-o", "src/api/schema.d.ts"], {
  cwd: resolve(import.meta.dirname, ".."),
  stdio: "inherit",
});
