import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { spawn } from "node:child_process";

const port = 4175;
const npmCli = process.env.npm_execpath;
const command = npmCli ? process.execPath : "npm";
const args = npmCli
  ? [npmCli, "run", "dev:h5", "--", "--host", "127.0.0.1", "--port", String(port), "--strictPort"]
  : ["run", "dev:h5", "--", "--host", "127.0.0.1", "--port", String(port), "--strictPort"];
const server = spawn(command, args, { detached: process.platform !== "win32", stdio: "ignore" });

async function waitForPage() {
  for (let attempt = 0; attempt < 30; attempt += 1) {
    try {
      const response = await fetch(`http://127.0.0.1:${port}/`);
      if (response.ok) return response.text();
    } catch {
      // Dev server is still starting.
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error("H5 dev server did not become ready");
}

try {
  const [html, pagesSource, clientSource] = await Promise.all([
    waitForPage(),
    readFile(new URL("../src/pages.json", import.meta.url), "utf8"),
    readFile(new URL("../src/api/client.ts", import.meta.url), "utf8"),
  ]);
  const pages = JSON.parse(pagesSource);
  assert.match(html, /id="app"/);
  assert.equal(pages.pages.length, 4);
  assert.deepEqual(
    pages.tabBar.list.map((item) => item.text),
    ["衣橱", "推荐", "风格", "历史"],
  );
  for (const path of [
    "/api/wardrobe/upload",
    "/api/profile/style-dna/draft",
    "/api/recommend",
    "/api/feedback",
    "/api/history",
  ]) {
    assert.ok(clientSource.includes(path), `missing API call: ${path}`);
  }
  assert.ok(
    clientSource.includes('`/api/wardrobe/${id}/confirm`, "POST"'),
    "confirm route must exist and use POST",
  );
  console.log("H5 smoke passed: shell and critical API calls configured");
} finally {
  if (server.pid) {
    if (process.platform === "win32") server.kill();
    else process.kill(-server.pid, "SIGTERM");
  }
}
