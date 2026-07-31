import assert from "node:assert/strict";
import test from "node:test";

import {
  mapRecommendation,
  mapStyleReference,
  mapWardrobeItem,
  seasonCode,
  waitForReady,
} from "../src/lib/api.mjs";

test("maps backend wardrobe records into the unchanged Stitch card model", () => {
  assert.deepEqual(
    mapWardrobeItem({
      id: "shirt-1",
      brand: "J.CREW",
      name: "青年布衬衫",
      category: "shirt",
      image_url: "/media/shirt-1.nobg.png",
    }),
    {
      id: "shirt-1",
      brand: "J.CREW",
      name: "青年布衬衫",
      category: "上装",
      imageUrl: "/media/shirt-1.nobg.png",
    },
  );
});

test("maps analyzed references into archive cards", () => {
  const mapped = mapStyleReference({
    id: "ref-1",
    image_url: "/media/look.jpg",
    status: "ready",
    added_at: "2026-07-30T10:00:00",
    analysis: {
      style_keywords: ["IvyStyle"],
      palette: ["海军蓝"],
      notable_elements: ["Layering"],
    },
  });
  assert.equal(mapped.title, "IvyStyle");
  assert.deepEqual(mapped.tags, ["#IvyStyle", "#Layering", "#海军蓝"]);
  assert.equal(mapped.imageUrl, "/media/look.jpg");
});

test("maps three real wardrobe recommendations into Safe Fresh Stretch cards", () => {
  const mapped = mapRecommendation({
    safe: {
      history_id: "history-safe",
      reason: "经典通勤",
      weather_fit: "适合 22°C",
      occasion_fit: "适合通勤",
      items: [
        { id: "top", name: "白衬衫", category: "top", image_url: "/media/top.png" },
        { id: "bottom", name: "藏青西裤", category: "bottom", image_url: "/media/bottom.png" },
        { id: "shoes", name: "乐福鞋", category: "shoes", image_url: "/media/shoes.png" },
      ],
    },
    fresh: { history_id: "history-fresh", reason: "清爽", weather_fit: "适合", occasion_fit: "适合", items: [] },
    stretch: { history_id: "history-stretch", reason: "突破", weather_fit: "适合", occasion_fit: "适合", items: [] },
  });
  assert.equal(mapped.safe.historyId, "history-safe");
  assert.equal(mapped.safe.items[0].name, "白衬衫");
  assert.equal(mapped.safe.description, "白衬衫 + 藏青西裤 + 乐福鞋");
  assert.equal(mapped.fresh.title, "Look 02 / 新鲜 (FRESH)");
  assert.equal(mapped.stretch.title, "Look 03 / 突破 (STRETCH)");
});

test("converts Stitch season labels to backend values", () => {
  assert.equal(seasonCode("春"), "spring");
  assert.equal(seasonCode("夏"), "summer");
  assert.equal(seasonCode("秋"), "autumn");
  assert.equal(seasonCode("冬"), "winter");
});

test("polls analysis until the backend returns ready", async () => {
  const states = [{ status: "pending" }, { status: "analyzing" }, { status: "ready", id: "item-1" }];
  const result = await waitForReady(() => Promise.resolve(states.shift()), { delay: 0 });
  assert.equal(result.id, "item-1");
});

test("keeps polling through slow first-time background setup", async () => {
  const states = [
    ...Array.from({ length: 120 }, () => ({ status: "analyzing" })),
    { status: "ready", id: "item-slow" },
  ];
  const result = await waitForReady(() => Promise.resolve(states.shift()), { delay: 0 });
  assert.equal(result.id, "item-slow");
});

test("stops polling when analysis fails", async () => {
  await assert.rejects(
    () => waitForReady(() => Promise.resolve({ status: "failed" }), { delay: 0 }),
    /识别失败/,
  );
});
