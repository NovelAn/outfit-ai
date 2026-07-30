import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const read = (path) => readFile(new URL(`../${path}`, import.meta.url), "utf8");

const [app, nav, html, pkg] = await Promise.all([
  read("src/App.tsx"),
  read("src/components/BottomNav.tsx"),
  read("index.html"),
  read("package.json"),
]);

for (const screen of ["ScreenToday", "ScreenWardrobe", "ScreenInspiration", "ScreenArchive", "ScreenProfile"]) {
  assert.match(app, new RegExp(screen), `missing Stitch screen: ${screen}`);
}
assert.match(app, /currentScreen === 'archive'/, "inspiration archive must remain a separate screen");
assert.deepEqual(
  [...nav.matchAll(/id: '(today|wardrobe|inspiration|profile)'/g)].map((match) => match[1]),
  ["today", "wardrobe", "inspiration", "profile"],
);
assert.match(html, /Hanken\+Grotesk/);
assert.match(html, /Libre\+Caslon\+Text/);
assert.match(html, /Material\+Symbols\+Outlined/);
assert.equal(JSON.parse(pkg).dependencies.react, "^19.0.1");

console.log("Stitch visual contract passed: five screens and original design dependencies preserved");
