import assert from "node:assert/strict";
import test from "node:test";

import * as profileApi from "../src/lib/api.mjs";
import {
  api,
  categoryCode,
  createSingleFlight,
  mapRecommendation,
  mapStyleReference,
  mapWardrobeItem,
  seasonCode,
  settleInPairs,
  waitForReady,
} from "../src/lib/api.mjs";

test("maps canonical Style DNA palette names without positional fallback colors", () => {
  assert.equal(typeof profileApi.paletteHex, "function");
  assert.equal(profileApi.paletteHex("深蓝色"), "#162839");
  assert.equal(profileApi.paletteHex("米黄色"), "#D8C49A");
  assert.equal(profileApi.paletteHex("浅蓝色"), "#A9C7DD");
  assert.equal(profileApi.paletteHex("不存在的颜色"), null);
  assert.equal(profileApi.paletteHex("constructor"), null);
});

test("keeps pinned tags visible when an alias is also hidden", () => {
  assert.equal(typeof profileApi.visibleStyleTags, "function");
  assert.deepEqual(
    profileApi.visibleStyleTags(
      ["日杂休闲", "轻量叠穿"],
      {
        pinned: ["日杂休闲"],
        hidden: ["日系松弛"],
        aliases: { "日杂休闲": "日系松弛" },
      },
      7,
    ),
    ["日系松弛", "轻量叠穿"],
  );
});

test("maps backend wardrobe records into the unchanged Stitch card model", () => {
  assert.deepEqual(
    mapWardrobeItem({
      id: "shirt-1",
      brand: "J.CREW",
      name: "青年布衬衫",
      category: "shirt",
      image_url: "/media/shirt-1.nobg.png",
      primary_color: null,
      secondary_color: null,
      material: null,
      fit: null,
      styles: [],
      tags: [],
      seasons: [],
      occasions: [],
    }),
    {
      id: "shirt-1",
      brand: "J.CREW",
      name: "青年布衬衫",
      category: "上装",
      imageUrl: "/media/shirt-1.nobg.png",
      primaryColor: "",
      secondaryColor: "",
      material: "",
      fit: "",
      styles: [],
      tags: [],
      seasons: [],
      occasions: [],
      thickness: "",
    },
  );
});

test("maps editable wardrobe attributes and controlled thickness tags", () => {
  const mapped = mapWardrobeItem({
    id: "item-1",
    category: "top",
    image_url: "/media/item-1.nobg.png",
    primary_color: "浅蓝色",
    secondary_color: "白色",
    material: "棉",
    fit: "宽松",
    styles: ["日系休闲"],
    tags: ["轻薄", "条纹"],
    seasons: ["春", "夏"],
    occasions: ["日常"],
  });

  assert.deepEqual(mapped, {
    id: "item-1",
    brand: "",
    name: "待确认单品",
    category: "上装",
    imageUrl: "/media/item-1.nobg.png",
    primaryColor: "浅蓝色",
    secondaryColor: "白色",
    material: "棉",
    fit: "宽松",
    styles: ["日系休闲"],
    tags: ["轻薄", "条纹"],
    seasons: ["春", "夏"],
    occasions: ["日常"],
    thickness: "轻薄",
  });
});

test("updates a wardrobe item through the PATCH endpoint", async () => {
  const originalFetch = globalThis.fetch;
  let captured;
  globalThis.fetch = async (url, options) => {
    captured = { url, options };
    return new Response(JSON.stringify({ id: "item-1", name: "条纹衬衫" }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };

  try {
    const result = await api.updateWardrobe("item-1", { name: "条纹衬衫" });
    assert.equal(result.name, "条纹衬衫");
    assert.equal(captured.url, "/api/wardrobe/item-1");
    assert.equal(captured.options.method, "PATCH");
    assert.equal(captured.options.headers["Content-Type"], "application/json");
    assert.deepEqual(JSON.parse(captured.options.body), { name: "条纹衬衫" });
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("groups wardrobe items into the five user-facing categories", () => {
  assert.equal(mapWardrobeItem({ id: "coat", category: "outerwear" }).category, "上装");
  assert.equal(mapWardrobeItem({ id: "dress", category: "dress" }).category, "下装");
  assert.equal(mapWardrobeItem({ id: "belt", category: "accessory" }).category, "配饰");
  assert.equal(categoryCode("配饰"), "accessory");
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

test("localizes failed inspiration status for archive cards", () => {
  const mapped = mapStyleReference({
    id: "ref-failed",
    image_url: "/media/look.jpg",
    status: "failed",
  });

  assert.equal(mapped.badge, "处理失败");
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

test("processes at most two wardrobe uploads concurrently", async () => {
  let active = 0;
  let peak = 0;
  const releases = [];
  const worker = async (value) => {
    active += 1;
    peak = Math.max(peak, active);
    await new Promise((resolve) => releases.push(resolve));
    active -= 1;
    return value;
  };

  const processing = settleInPairs([1, 2, 3], worker);
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(peak, 2);
  assert.equal(releases.length, 2);
  releases.shift()();
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(releases.length, 2);
  releases.splice(0).forEach((release) => release());

  assert.deepEqual(await processing, [
    { status: "fulfilled", value: 1 },
    { status: "fulfilled", value: 2 },
    { status: "fulfilled", value: 3 },
  ]);
});

test("settles failed wardrobe uploads without stopping the batch", async () => {
  const visited = [];

  const results = await settleInPairs([1, 2, 3], async (value) => {
    visited.push(value);
    if (value === 2) throw new Error("failed");
    return value;
  });

  assert.deepEqual(visited.sort(), [1, 2, 3]);
  assert.deepEqual(results.map(({ status }) => status), [
    "fulfilled",
    "rejected",
    "fulfilled",
  ]);
});

test("ignores a second batch start while the first is still running", async () => {
  const run = createSingleFlight();
  let release;
  let calls = 0;
  const first = run(async () => {
    calls += 1;
    await new Promise((resolve) => { release = resolve; });
  });

  assert.equal(await run(async () => { calls += 1; }), false);
  assert.equal(calls, 1);
  release();
  assert.equal(await first, true);
  assert.equal(await run(async () => { calls += 1; }), true);
  assert.equal(calls, 2);
});
