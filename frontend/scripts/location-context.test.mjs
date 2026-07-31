import assert from "node:assert/strict";
import test from "node:test";

import { resolveLocationContext } from "../src/lib/location.mjs";

const memoryStorage = (initial = {}) => {
  const values = new Map(Object.entries(initial));
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
    removeItem: (key) => values.delete(key),
  };
};

const fakeGeolocation = ({ latitude, longitude }) => ({
  getCurrentPosition: (success) => success({ coords: { latitude, longitude } }),
});

const deniedGeolocation = () => ({
  getCurrentPosition: (_success, failure) => failure(new Error("denied")),
});

test("uses rounded current coordinates when permission succeeds", async () => {
  const context = await resolveLocationContext({
    geolocation: fakeGeolocation({ latitude: 31.230416, longitude: 121.473701 }),
    storage: memoryStorage(),
    now: () => new Date("2026-07-31T08:00:00+08:00"),
  });
  assert.equal(context.latitude, 31.23);
  assert.equal(context.longitude, 121.474);
  assert.equal(context.source, "current");
});

test("falls back from denied location to cached coordinates, then manual city", async () => {
  const storage = memoryStorage({
    OUTFIT_AI_LOCATION: JSON.stringify({
      latitude: 31.23,
      longitude: 121.474,
      updatedAt: "2026-07-31T07:30:00.000Z",
    }),
    OUTFIT_AI_CITY: "上海",
  });
  const cached = await resolveLocationContext({
    geolocation: deniedGeolocation(),
    storage,
    now: () => new Date("2026-07-31T08:00:00.000Z"),
  });
  assert.equal(cached.source, "cached");
  storage.removeItem("OUTFIT_AI_LOCATION");
  const manual = await resolveLocationContext({
    geolocation: deniedGeolocation(),
    storage,
    now: () => new Date("2026-07-31T08:00:00.000Z"),
  });
  assert.deepEqual(manual, { city: "上海", source: "manual" });
});
