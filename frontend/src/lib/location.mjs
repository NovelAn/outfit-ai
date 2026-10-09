const CACHE_KEY = "OUTFIT_AI_LOCATION";
const CITY_KEY = "OUTFIT_AI_CITY";
const LOCATION_MODE_KEY = "OUTFIT_AI_LOCATION_MODE";
const TARGET_DATE_KEY = "OUTFIT_AI_TARGET_DATE";
const SELECTED_LOCATION_KEY = "OUTFIT_AI_SELECTED_LOCATION";
const CACHE_MAX_AGE_MS = 2 * 60 * 60 * 1000;
const GEOLOCATION_TIMEOUT_MS = 8_000;
const GEOLOCATION_MAX_AGE_MS = 5 * 60 * 1000;

const validTargetDate = (value, now = new Date()) => {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value || "")) return false;
  const target = new Date(`${value}T00:00:00`);
  const today = new Date(now);
  today.setHours(0, 0, 0, 0);
  const days = (target.getTime() - today.getTime()) / 86_400_000;
  return Number.isInteger(days) && days >= 0 && days <= 14;
};

const readTargetDate = (storage, now) => {
  try {
    const value = storage?.getItem(TARGET_DATE_KEY);
    return validTargetDate(value, now()) ? value : null;
  } catch {
    return null;
  }
};

const withTargetDate = (context, storage, now) => {
  const targetDate = readTargetDate(storage, now);
  return targetDate ? { ...context, target_date: targetDate } : context;
};

const readSelectedLocation = (storage) => {
  try {
    const value = JSON.parse(storage?.getItem(SELECTED_LOCATION_KEY) || "null");
    return value?.city && validCoordinates(value)
      ? { city: value.city, latitude: roundCoordinate(value.latitude), longitude: roundCoordinate(value.longitude) }
      : null;
  } catch {
    return null;
  }
};

export const saveLocationCandidate = (candidate, storage = globalThis.localStorage) => {
  if (!candidate?.name || !validCoordinates(candidate)) return false;
  try {
    storage?.setItem(
      SELECTED_LOCATION_KEY,
      JSON.stringify({
        city: candidate.name,
        latitude: roundCoordinate(candidate.latitude),
        longitude: roundCoordinate(candidate.longitude),
      }),
    );
    storage?.setItem(CITY_KEY, candidate.name);
    storage?.setItem(LOCATION_MODE_KEY, "manual");
    return true;
  } catch {
    return false;
  }
};

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

const currentCoordinates = (geolocation, timeoutMs = GEOLOCATION_TIMEOUT_MS) =>
  new Promise((resolve, reject) => {
    if (!geolocation?.getCurrentPosition) return reject(new Error("geolocation unavailable"));
    let settled = false;
    const finish = (callback, value) => {
      if (settled) return;
      settled = true;
      clearTimeout(timeoutId);
      callback(value);
    };
    const timeoutId = setTimeout(() => finish(reject, new Error("geolocation timeout")), timeoutMs);
    geolocation.getCurrentPosition(
      ({ coords }) => finish(resolve, { latitude: roundCoordinate(coords.latitude), longitude: roundCoordinate(coords.longitude) }),
      (error) => finish(reject, error),
      {
        enableHighAccuracy: true,
        maximumAge: GEOLOCATION_MAX_AGE_MS,
        timeout: timeoutMs,
      },
    );
  });

export async function resolveLocationContext({
  geolocation = globalThis.navigator?.geolocation,
  storage = globalThis.localStorage,
  now = () => new Date(),
  geolocationTimeoutMs = GEOLOCATION_TIMEOUT_MS,
} = {}) {
  try {
    const mode = storage?.getItem(LOCATION_MODE_KEY);
    const city = storage?.getItem(CITY_KEY)?.trim();
    const selected = readSelectedLocation(storage);
    if (mode === "manual" && city) {
      const context = selected?.city === city ? { ...selected, source: "manual" } : { city, source: "manual" };
      return withTargetDate(context, storage, now);
    }
  } catch {
    // Invalid local storage must not prevent automatic location lookup.
  }

  try {
    const coordinates = await currentCoordinates(geolocation, geolocationTimeoutMs);
    if (validCoordinates(coordinates)) {
      try {
        storage?.setItem(CACHE_KEY, JSON.stringify({ ...coordinates, updatedAt: now().toISOString() }));
      } catch {
        // The current location is still usable when local storage is blocked.
      }
      return withTargetDate({ ...coordinates, source: "current" }, storage, now);
    }
  } catch {
    // Fall through to cached coordinates, then the user's manual city.
  }

  const cached = readCachedLocation(storage, now);
  if (cached) return withTargetDate(cached, storage, now);

  try {
    const city = storage?.getItem(CITY_KEY)?.trim();
    if (city) return withTargetDate({ city, source: "manual" }, storage, now);
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
  refreshTier = null,
  targetDate = null,
}) {
  const references = await api.references().catch(() => []);
  return api.recommend({
    occasion: "日常",
    scene: "日常",
    city: weather?.city || context.city,
    latitude: context.latitude,
    longitude: context.longitude,
    ...((targetDate || context.target_date || weather?.target_date || weather?.local_date)
      ? { target_date: targetDate || context.target_date || weather?.target_date || weather?.local_date }
      : {}),
    ...(forceRefresh ? { force_refresh: true } : {}),
    ...(refreshTier ? { refresh_tier: refreshTier } : {}),
    reference_ids: references
      .filter((item) => item.status === "ready")
      .slice(0, 6)
      .map((item) => item.id),
    locked_item_ids: [],
  });
}
