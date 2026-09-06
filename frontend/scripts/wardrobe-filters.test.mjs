import assert from "node:assert/strict";
import test from "node:test";
import {
  filterWardrobeItems,
  wardrobeFeatureTags,
  wardrobeInfoTags,
  toggleFilterValue,
} from "../src/lib/wardrobe-filters.mjs";

const items = [
  { id: "a", category: "上装", seasons: ["春", "夏"], thickness: "轻薄" },
  { id: "b", category: "下装", seasons: ["夏"], thickness: "适中" },
  { id: "c", category: "下装", seasons: ["秋"], thickness: "厚实" },
];

test("wardrobe filters use OR within a group and AND across groups", () => {
  const result = filterWardrobeItems(items, {
    category: "下装",
    seasons: ["春", "夏"],
    thicknesses: ["轻薄", "适中"],
  });

  assert.deepEqual(result.map((item) => item.id), ["b"]);
});

test("empty filter groups leave the item order unchanged", () => {
  assert.deepEqual(
    filterWardrobeItems(items, { category: "全部", seasons: [], thicknesses: [] }).map(
      (item) => item.id,
    ),
    ["a", "b", "c"],
  );
  assert.deepEqual(
    filterWardrobeItems(items, {
      category: "全部",
      seasons: ["春", "夏", "秋", "冬"],
      thicknesses: [],
    }).map((item) => item.id),
    ["a", "b", "c"],
  );
});

test("season shortcut selects all seasons without storing a fifth value", () => {
  const seasons = ["春", "夏", "秋", "冬"];
  assert.deepEqual(toggleFilterValue([], "四季", seasons), seasons);
  assert.deepEqual(toggleFilterValue(seasons, "四季", seasons), []);
  assert.deepEqual(toggleFilterValue(seasons, "夏", seasons), ["春", "秋", "冬"]);
});

test("builds visible item info tags for seasons and thickness", () => {
  assert.deepEqual(
    wardrobeInfoTags({ seasons: ["春", "夏"], thickness: "轻薄" }),
    ["春", "夏", "·", "轻薄"],
  );
});

test("keeps thickness out of the regular feature tags", () => {
  assert.deepEqual(
    wardrobeFeatureTags({ tags: ["水洗效果", "适中", "五口袋设计"] }),
    ["水洗效果", "五口袋设计"],
  );
});
