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
  assert.equal(pages.pages.length, 5);
  assert.deepEqual(
    pages.tabBar.list.map((item) => item.text),
    ["今日", "衣橱", "灵感", "我的"],
  );
  for (const path of [
    "/api/wardrobe/upload",
    "/api/style-references/upload",
    "/api/style-references",
    "/api/recommend",
    "/api/inspiration/generate",
    "/api/feedback",
    "/api/history",
  ]) {
    assert.ok(clientSource.includes(path), `missing API call: ${path}`);
  }
  assert.ok(
    clientSource.includes('`/api/wardrobe/${id}/confirm`, "POST"'),
    "confirm route must exist and use POST",
  );
  const inspirationSource = await readFile(
    new URL("../src/pages/inspiration/index.vue", import.meta.url),
    "utf8",
  );
  assert.match(inspirationSource, /AI 灵感图 · 不代表衣橱已有单品/);
  assert.doesNotMatch(clientSource, /request:fail/);
  console.log("H5 smoke passed: shell and critical API calls configured");
} finally {
  if (server.pid) {
    if (process.platform === "win32") server.kill();
    else process.kill(-server.pid, "SIGTERM");
  }
}
