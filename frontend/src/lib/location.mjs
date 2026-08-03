const CACHE_KEY = "OUTFIT_AI_LOCATION";
const CITY_KEY = "OUTFIT_AI_CITY";
const CACHE_MAX_AGE_MS = 24 * 60 * 60 * 1000;
const GEOLOCATION_TIMEOUT_MS = 8_000;

const roundCoordinate = (value) => Number(Number(value).toFixed(3));

const validCoordinates = ({ latitude, longitude } = {}) =>
  Number.isFinite(latitude) &&
  Number.isFinite(longitude) &&
  latitude >= -90 &&
  latitude <= 90 &&
  longitude >= -180 &&
  longitude <= 180;

const readCachedLocation = (storage, now) => {
  try {
    const cached = JSON.parse(storage.getItem(CACHE_KEY) || "null");
    const updatedAt = new Date(cached?.updatedAt).getTime();
    const age = now().getTime() - updatedAt;
    if (validCoordinates(cached) && age >= 0 && age <= CACHE_MAX_AGE_MS) {
      return { latitude: cached.latitude, longitude: cached.longitude, source: "cached" };
    }
  } catch {
    // Invalid local storage must not prevent manual-city fallback.
  }
  return null;
};

const currentCoordinates = (geolocation) =>
  new Promise((resolve, reject) => {
    if (!geolocation?.getCurrentPosition) return reject(new Error("geolocation unavailable"));
    geolocation.getCurrentPosition(
      ({ coords }) => resolve({ latitude: roundCoordinate(coords.latitude), longitude: roundCoordinate(coords.longitude) }),
      reject,
      { timeout: GEOLOCATION_TIMEOUT_MS },
    );
  });

export async function resolveLocationContext({
  geolocation = globalThis.navigator?.geolocation,
  storage = globalThis.localStorage,
  now = () => new Date(),
} = {}) {
  try {
    const coordinates = await currentCoordinates(geolocation);
    if (validCoordinates(coordinates)) {
      try {
        storage?.setItem(CACHE_KEY, JSON.stringify({ ...coordinates, updatedAt: now().toISOString() }));
      } catch {
        // The current location is still usable when local storage is blocked.
      }
      return { ...coordinates, source: "current" };
    }
  } catch {
    // Fall through to cached coordinates, then the user's manual city.
  }

  const cached = readCachedLocation(storage, now);
  if (cached) return cached;

  try {
    const city = storage?.getItem(CITY_KEY)?.trim();
    if (city) return { city, source: "manual" };
  } catch {
    // Missing local storage is the same as no configured city.
  }
  return { source: "missing" };
}

export async function loadDailyRecommendation({
  api,
  context,
  weather,
  forceRefresh = false,
}) {
  const references = await api.references().catch(() => []);
  return api.recommend({
    occasion: "日常",
    scene: "日常",
    city: weather?.city || context.city,
    latitude: context.latitude,
    longitude: context.longitude,
    ...(forceRefresh ? { force_refresh: true } : {}),
    reference_ids: references
      .filter((item) => item.status === "ready")
      .slice(0, 6)
      .map((item) => item.id),
    locked_item_ids: [],
  });
}
