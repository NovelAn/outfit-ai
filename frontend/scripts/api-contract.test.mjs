import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import * as profileApi from "../src/lib/api.mjs";
import { compactLookItems } from "../src/lib/look-layout.mjs";
import { displayWeatherForRecommendation, lookFeedbackKey } from "../src/lib/today-state.mjs";
import {
  api,
  categoryCode,
  createSingleFlight,
  confirmFeedback,
  mapHistoryLook,
  requireHistoryId,
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

test("maps every 3–6 item Look, including optional layers and accessories", () => {
  const mapped = mapRecommendation({
    safe: {
      history_id: "history-full-look",
      items: [
        { id: "coat", name: "风衣", category: "outerwear", image_url: "/media/coat.png" },
        { id: "shirt", name: "衬衫", category: "top", image_url: "/media/shirt.png" },
        { id: "pants", name: "长裤", category: "bottom", image_url: "/media/pants.png" },
        { id: "shoes", name: "乐福鞋", category: "shoes", image_url: "/media/shoes.png" },
        { id: "watch", name: "腕表", category: "accessory", image_url: "/media/watch.png" },
      ],
    },
  });

  assert.equal(mapped.safe.lookItems.length, 5);
  assert.equal(mapped.safe.lookItems[0].category, "上装");
  assert.equal(mapped.safe.lookItems[4].category, "配饰");
});

test("maps scoped history into a full-Look memo model with legacy image fallback", () => {
  const mapped = mapHistoryLook(
    {
      id: "history-1",
      date: "2026-08-04",
      pick_mode: "fresh",
      action: "saved",
      rating: 5,
      scope: "archive",
      reason: "适合通勤",
      item_ids: ["shirt", "pants", "shoes", "watch"],
      collage_path: "/media/legacy-collage.png",
    },
    new Map([
      ["shirt", { name: "衬衫", category: "上装", imageUrl: "/media/shirt.png" }],
      ["pants", { name: "长裤", category: "下装", imageUrl: "/media/pants.png" }],
      ["shoes", { name: "乐福鞋", category: "鞋履", imageUrl: "/media/shoes.png" }],
      ["watch", { name: "腕表", category: "配饰", imageUrl: "/media/watch.png" }],
    ]),
  );

  assert.equal(mapped.historyId, "history-1");
  assert.equal(mapped.rating, 5);
  assert.equal(mapped.scope, "archive");
  assert.equal(mapped.lookItems.length, 4);
  assert.equal(mapped.imageUrl, "/media/shirt.png");
  assert.equal(mapHistoryLook({ id: "legacy", item_ids: [], collage_path: "/media/legacy.png" }, new Map()).imageUrl, "/media/legacy.png");
});

test("uses a collage only when no history items resolve", () => {
  const wardrobe = new Map([["shirt", { name: "衬衫", category: "上装", imageUrl: "/media/shirt.png" }]]);
  const zero = mapHistoryLook({ id: "zero", item_ids: ["missing"], collage_path: "/media/collage.png" }, wardrobe);
  const partial = mapHistoryLook({ id: "partial", item_ids: ["shirt", "missing"], collage_path: "/media/collage.png" }, wardrobe);

  assert.deepEqual(zero.lookItems, []);
  assert.equal(zero.imageUrl, "/media/collage.png");
  assert.deepEqual(partial.lookItems.map((item) => item.name), ["衬衫"]);
  assert.equal(partial.imageUrl, "/media/shirt.png");
});

test("translates network failures and sends a requested history scope", async () => {
  const originalFetch = globalThis.fetch;
  let requestedUrl;
  globalThis.fetch = async (url) => {
    requestedUrl = url;
    throw new TypeError("Failed to fetch");
  };
  try {
    await assert.rejects(() => api.history({ scope: "archive" }), /网络连接失败，请检查网络后重试/);
    assert.equal(requestedUrl, "/api/history?scope=archive");
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("commits feedback only after the server accepts it and rolls back on failure", async () => {
  const calls = [];
  await assert.rejects(
    () => confirmFeedback(
      async () => { throw new Error("推荐历史不存在"); },
      { history_id: "missing", items_worn: [], action: "saved" },
      () => calls.push("commit"),
      () => calls.push("rollback"),
    ),
    /推荐历史不存在/,
  );
  assert.deepEqual(calls, ["rollback"]);

  await confirmFeedback(
    async () => ({ ok: true }),
    { history_id: "history-1", items_worn: [], rating: 5 },
    () => calls.push("commit"),
    () => calls.push("rollback"),
  );
  assert.deepEqual(calls, ["rollback", "commit"]);
});

test("refuses persistent Look feedback without a server history identity", () => {
  assert.equal(requireHistoryId("history-1"), "history-1");
  assert.throws(() => requireHistoryId(), /尚未生成可反馈的推荐历史/);
  const today = readFileSync(new URL("../src/components/ScreenToday.tsx", import.meta.url), "utf8");
  const profile = readFileSync(new URL("../src/components/ScreenProfile.tsx", import.meta.url), "utf8");
  assert.match(today, /historyId = requireHistoryId/);
  assert.match(profile, /historyId = requireHistoryId/);
});

test("uses a compact two-column Look collage", () => {
  const today = readFileSync(new URL("../src/components/ScreenToday.tsx", import.meta.url), "utf8");
  assert.match(today, /compact-look-collage/);
  assert.match(today, /grid-cols-2/);
  assert.match(today, /look-item-rail/);
  assert.doesNotMatch(today, /vertical-stack-img/);
});

test("keeps feedback order while promoting a hat and railing remaining Look items", () => {
  const today = readFileSync(new URL("../src/components/ScreenToday.tsx", import.meta.url), "utf8");
  assert.match(today, /items_worn: look\.items\.map\(\(item: any\) => item\.id\)/);

  for (const count of [4, 5, 6]) {
    const items = [
      { id: "top", category: "上装", name: "T恤" },
      { id: "bottom", category: "下装", name: "长裤" },
      { id: "shoes", category: "鞋履", name: "跑鞋" },
      { id: "hat", category: "配饰", name: "渔夫帽" },
      { id: "layer", category: "上装", name: "工装背心" },
      { id: "bag", category: "配饰", name: "托特包" },
    ].slice(0, count);
    const apiOrder = items.map((item) => item.id);

    const { primaryItems, railItems } = compactLookItems(items);

    assert.equal(primaryItems[0].id, "hat");
    const feedbackHistoryIds = items.map((item) => item.id);
    assert.deepEqual(items.map((item) => item.id), apiOrder);
    assert.deepEqual(feedbackHistoryIds, apiOrder, "feedback/history IDs retain API order");
    assert.deepEqual(railItems.map((item) => item.id), ["shoes", "layer", "bag"].slice(0, count - 3));
  }
});

test("keys Today feedback by history identity and preserves freshly fetched weather", () => {
  const liveWeather = { city: "上海", temp: 31, local_date: "2026-08-04" };
  const reusedRecommendation = { weather: { city: "上海", temp: 22, local_date: "2026-08-03" } };
  const oldLook = { historyId: "history-old" };
  const newLook = { historyId: "history-new" };
  const liked = { [lookFeedbackKey(oldLook)]: true };
  const ratings = { [lookFeedbackKey(oldLook)]: { rating: 5 } };

  assert.equal(displayWeatherForRecommendation(liveWeather, reusedRecommendation), liveWeather);
  assert.equal(lookFeedbackKey(newLook), "history-new");
  assert.equal(liked[lookFeedbackKey(newLook)], undefined);
  assert.equal(ratings[lookFeedbackKey(newLook)], undefined);

  const today = readFileSync(new URL("../src/components/ScreenToday.tsx", import.meta.url), "utf8");
  assert.match(today, /applyRecommendation\(recommendation, latestWeather\)/);
  assert.match(today, /items_worn: look\.items\.map\(\(item: any\) => item\.id\)/);
});

test("reuses Total Look thumbnails throughout profile history surfaces without fabricated garments", () => {
  const profile = readFileSync(new URL("../src/components/ScreenProfile.tsx", import.meta.url), "utf8");
  assert.ok((profile.match(/<TotalLookThumbnails/g) || []).length >= 5);
  assert.doesNotMatch(profile, /images\.unsplash\.com/);
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
