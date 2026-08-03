import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const read = (path) => readFile(new URL(`../${path}`, import.meta.url), "utf8");

const [app, nav, html, pkg, inspiration, archive, wardrobe, today, drawer, profile] = await Promise.all([
  read("src/App.tsx"),
  read("src/components/BottomNav.tsx"),
  read("index.html"),
  read("package.json"),
  read("src/components/ScreenInspiration.tsx"),
  read("src/components/ScreenArchive.tsx"),
  read("src/components/ScreenWardrobe.tsx"),
  read("src/components/ScreenToday.tsx"),
  read("src/components/SideDrawer.tsx"),
  read("src/components/ScreenProfile.tsx"),
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
assert.match(wardrobe, /编辑信息/, "wardrobe detail must expose an edit entry");
assert.match(wardrobe, /删除单品/, "wardrobe detail must expose a delete entry");
assert.match(wardrobe, /保存修改/, "wardrobe edit modal must expose a save action");
assert.match(wardrobe, /确认删除/, "wardrobe delete must require in-modal confirmation");
assert.match(wardrobe, /api\.updateWardrobe/, "wardrobe edit must call the PATCH API");
assert.match(wardrobe, /api\.deleteWardrobe/, "wardrobe delete must call the DELETE API");
assert.doesNotMatch(today, /TOKYO \/ 24°C/);
assert.match(today, /resolveLocationContext/);
assert.match(today, /precipitation_probability_max/);
assert.match(drawer, /OpenStreetMap contributors/);
assert.match(drawer, /正在学习/, "drawer must use evidence-based cold-start learning copy");
assert.match(drawer, /已根据/, "drawer must describe the feedback evidence used");
assert.doesNotMatch(drawer, /%\s*Match|85\s*\+\s*ratingsCount\s*\*\s*4/, "drawer must not display a fake match percentage");
assert.match(profile, /coreTags\s*=\s*visibleStyleTags\(profile\?\.style_keywords\s*\|\|\s*\[\], tagPreferences, 7\)/, "profile summary must cap core tags at seven");
assert.match(profile, /recent_style_signals/, "profile must render recent style signals separately");
assert.match(profile, /管理标签/, "profile must expose tag management");
assert.match(profile, /正在学习/, "profile must use evidence-based cold-start learning copy");
assert.match(profile, /已根据/, "profile must describe the feedback evidence used");
assert.doesNotMatch(profile, /85\s*\+\s*ratingCount\s*\*\s*4/, "profile must not calculate a fake match percentage");

console.log("Stitch visual contract passed: five screens and original design dependencies preserved");
