import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const read = (path) => readFile(new URL(`../${path}`, import.meta.url), "utf8");

const [app, nav, html, pkg, inspiration, archive, wardrobe] = await Promise.all([
  read("src/App.tsx"),
  read("src/components/BottomNav.tsx"),
  read("index.html"),
  read("package.json"),
  read("src/components/ScreenInspiration.tsx"),
  read("src/components/ScreenArchive.tsx"),
  read("src/components/ScreenWardrobe.tsx"),
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
assert.match(inspiration, /input\.multiple = true/, "inspiration upload must accept multiple files");
assert.match(inspiration, /Promise\.allSettled/, "one failed reference must not stop the batch");
assert.match(archive, /grid-cols-3/, "mobile archive must use a compact three-column grid");
assert.match(archive, /aspect-\[3\/4\]/, "archive thumbnails must use a fixed crop");
assert.match(
  archive,
  /<img\s+onClick=\{\(\) => setPreviewItem\(null\)\}/,
  "clicking the enlarged image must restore the archive",
);
assert.match(wardrobe, /首次处理.*去背景模型/, "wardrobe must explain slow first-time setup");
assert.match(wardrobe, /grid-cols-3/, "mobile wardrobe must show three compact columns");
assert.match(wardrobe, /aspect-\[4\/5\]/, "wardrobe thumbnails must use a compact fixed ratio");

console.log("Stitch visual contract passed: five screens and original design dependencies preserved");
