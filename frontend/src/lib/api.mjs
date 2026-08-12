const API_BASE = (import.meta.env?.VITE_API_BASE_URL || "").replace(/\/$/, "");

const TIER_META = {
  safe: { title: "Look 01 / 稳妥 (SAFE)", tag: "日杂经典" },
  fresh: { title: "Look 02 / 新鲜 (FRESH)", tag: "松弛休假" },
  stretch: { title: "Look 03 / 突破 (STRETCH)", tag: "工装廓形" },
};

export const PALETTE_HEX = {
  黑色: "#1B1C19", 白色: "#F7F5EF", 深蓝色: "#162839",
  浅蓝色: "#A9C7DD", 灰色: "#8A8D91", 米白色: "#EEE8DA",
  米黄色: "#D8C49A", 卡其色: "#B39B72", 棕色: "#7A5337",
  绿色: "#647B5B", 红色: "#9A442A", 紫色: "#75627D",
};

export function paletteHex(name) {
  return Object.hasOwn(PALETTE_HEX, name) ? PALETTE_HEX[name] : null;
}

export function visibleStyleTags(tags = [], preferences = {}, limit = 7) {
  const aliases = preferences.aliases || {};
  const normalize = (tag) => aliases[tag] || tag;
  const unique = (values) => [...new Set(values.filter(Boolean))];
  const normalizedTags = tags.map(normalize);
  const pinned = unique((preferences.pinned || []).map(normalize));
  const hidden = new Set((preferences.hidden || []).map(normalize));
  return unique([
    ...pinned.filter((tag) => normalizedTags.includes(tag)),
    ...normalizedTags,
  ]).filter((tag) => pinned.includes(tag) || !hidden.has(tag)).slice(0, limit);
}

function apiUrl(path) {
  return `${API_BASE}${path}`;
}

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(apiUrl(path), options);
  } catch (error) {
    throw new Error("网络连接失败，请检查网络后重试", { cause: error });
  }
  if (response.ok) {
    return response.status === 204 ? null : response.json();
  }
  let detail = `请求失败（${response.status}）`;
  try {
    const body = await response.json();
    if (typeof body.detail === "string") detail = body.detail;
  } catch {
    // Keep the status-based message when the server did not return JSON.
  }
  throw new Error(detail);
}

function upload(path, file) {
  const body = new FormData();
  body.append("file", file);
  return request(path, { method: "POST", body });
}

export function mediaUrl(path) {
  if (!path || /^(https?:|data:|blob:)/.test(path)) return path || "";
  return apiUrl(path.startsWith("/") ? path : `/${path}`);
}

function categoryLabel(category = "") {
  const value = category.toLowerCase();
  if (["top", "shirt", "t-shirt", "tee", "sweater", "knitwear", "outerwear", "jacket", "coat", "blazer", "cardigan"].includes(value)) return "上装";
  if (["bottom", "pants", "trousers", "jeans", "shorts", "skirt", "dress"].includes(value)) return "下装";
  if (["shoes", "shoe", "sneakers", "boots", "loafers", "derbies"].includes(value)) return "鞋履";
  if (["accessory", "accessories", "bag", "belt", "hat", "scarf", "jewelry", "watch"].includes(value)) return "配饰";
  return "上装";
}

export function categoryCode(label) {
  return { 上装: "top", 下装: "bottom", 鞋履: "shoes", 配饰: "accessory" }[label] || "top";
}

export function mapWardrobeItem(item) {
  const tags = Array.isArray(item.tags) ? item.tags : [];
  const thickness = tags.find((tag) => ["轻薄", "适中", "厚实"].includes(tag)) || "";
  return {
    id: item.id,
    brand: item.brand || "",
    name: item.name || "待确认单品",
    category: categoryLabel(item.category),
    imageUrl: mediaUrl(item.image_url),
    primaryColor: item.primary_color || "",
    secondaryColor: item.secondary_color || "",
    material: item.material || "",
    fit: item.fit || "",
    styles: Array.isArray(item.styles) ? item.styles : [],
    tags,
    seasons: Array.isArray(item.seasons) ? item.seasons : [],
    occasions: Array.isArray(item.occasions) ? item.occasions : [],
    thickness,
    ...(item.isNew ? { isNew: true } : {}),
  };
}

export function mapStyleReference(reference) {
  const analysis = reference.analysis || {};
  const keywords = analysis.style_keywords || [];
  const elements = analysis.notable_elements || [];
  const palette = analysis.palette || [];
  const tags = [...keywords, ...elements, ...palette]
    .filter(Boolean)
    .map((value) => `#${String(value).replace(/^#/, "")}`);
  const statusBadges = { pending: "等待中", analyzing: "分析中", failed: "处理失败" };
  return {
    id: reference.id,
    title: keywords[0] || "正在沉淀的灵感",
    category: keywords[0] || "Reference",
    imageUrl: mediaUrl(reference.image_url),
    analysis,
    tags,
    badge: statusBadges[reference.status],
    date: reference.added_at,
    status: reference.status,
  };
}

function mapLook(tier, look) {
  const items = (look.items || []).map((item) => ({
    id: item.id,
    name: item.name || "未命名单品",
    category: categoryLabel(item.category),
    img: mediaUrl(item.image_url),
    primaryColor: item.primary_color || "",
    secondaryColor: item.secondary_color || "",
    desc: [item.primary_color, item.category].filter(Boolean).join(" · "),
  }));
  return {
    ...TIER_META[tier],
    historyId: look.history_id,
    description: items.map((item) => item.name).join(" + "),
    reason: look.reason || "",
    weatherFit: look.weather_fit || "",
    occasionFit: look.occasion_fit || "",
    imageUrl: items[0]?.img || "",
    items,
    lookItems: items,
  };
}

export function mapHistoryLook(row, wardrobeById = new Map()) {
  const items = (row.item_ids || [])
    .map((id) => wardrobeById.get(id))
    .filter(Boolean)
    .map((item) => ({ name: item.name, category: item.category, img: item.imageUrl }));
  const tier = row.pick_mode === "safe" ? "稳妥" : row.pick_mode === "fresh" ? "新鲜" : "突破";
  return {
    id: row.id,
    historyId: row.id,
    title: `${tier} / ${row.occasion || "日常"}`,
    date: row.date,
    tag: String(row.pick_mode || "").toUpperCase(),
    imageUrl: items[0]?.img || mediaUrl(row.collage_path),
    description: row.reason || "",
    items,
    lookItems: items,
    itemIds: row.item_ids || [],
    action: row.action,
    rating: row.rating,
    woreIt: Boolean(row.wore_it),
    scope: row.scope,
  };
}

export async function confirmFeedback(submit, data, onConfirmed, onRollback) {
  try {
    const result = await submit(data);
    onConfirmed?.(result);
    return result;
  } catch (error) {
    onRollback?.(error);
    throw error;
  }
}

export function requireHistoryId(historyId) {
  if (!historyId) throw new Error("此 Look 尚未生成可反馈的推荐历史");
  return historyId;
}

export function mapRecommendation(result) {
  return {
    weather: result.weather,
    safe: mapLook("safe", result.safe || {}),
    fresh: mapLook("fresh", result.fresh || {}),
    stretch: mapLook("stretch", result.stretch || {}),
  };
}

export function seasonCode(label) {
  return { 春: "spring", 夏: "summer", 秋: "autumn", 冬: "winter" }[label];
}

export async function waitForReady(getStatus, { delay = 800, maxAttempts = 375 } = {}) {
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    const result = await getStatus();
    if (result.status === "ready") return result;
    if (result.status === "failed") throw new Error("AI 识别失败，请重新上传");
    if (delay) await new Promise((resolve) => setTimeout(resolve, delay));
  }
  throw new Error("AI 处理时间较长，任务仍在后台继续，请勿重复上传");
}

export async function settleInPairs(items, worker) {
  const results = Array(items.length);
  let next = 0;
  const run = async () => {
    while (next < items.length) {
      const index = next;
      next += 1;
      try {
        results[index] = { status: "fulfilled", value: await worker(items[index]) };
      } catch (reason) {
        results[index] = { status: "rejected", reason };
      }
    }
  };
  await Promise.all(Array.from({ length: Math.min(2, items.length) }, run));
  return results;
}

export function createSingleFlight() {
  let active = false;
  return async (worker) => {
    if (active) return false;
    active = true;
    try {
      await worker();
      return true;
    } finally {
      active = false;
    }
  };
}

export const api = {
  wardrobe: async () => (await request("/api/wardrobe/items")).map(mapWardrobeItem),
  wardrobeStatus: (id) => request(`/api/wardrobe/${id}/status`),
  uploadWardrobe: (file) => upload("/api/wardrobe/upload", file),
  confirmWardrobe: (id, data) =>
    request(`/api/wardrobe/${id}/confirm`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),
  updateWardrobe: (id, data) =>
    request(`/api/wardrobe/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),
  deleteWardrobe: (id) => request(`/api/wardrobe/${id}`, { method: "DELETE" }),
  references: async () => (await request("/api/style-references")).map(mapStyleReference),
  referenceStatus: (id) => request(`/api/style-references/${id}/status`),
  uploadReference: (file) => upload("/api/style-references/upload", file),
  deleteReference: (id) => request(`/api/style-references/${id}`, { method: "DELETE" }),
  profile: () => request("/api/profile"),
  saveProfile: (profile) =>
    request("/api/profile", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(profile),
    }),
  history: ({ scope, limit } = {}) => {
    const params = new URLSearchParams();
    if (scope) params.set("scope", scope);
    if (limit) params.set("limit", String(limit));
    const query = params.toString();
    return request(`/api/history${query ? `?${query}` : ""}`);
  },
  weather: ({ city, latitude, longitude } = {}) => {
    const params = new URLSearchParams();
    if (city) params.set("city", city);
    if (latitude !== undefined) params.set("latitude", String(latitude));
    if (longitude !== undefined) params.set("longitude", String(longitude));
    const query = params.toString();
    return request(`/api/weather${query ? `?${query}` : ""}`);
  },
  recommend: async (data) => {
    const { force_refresh, ...payload } = data;
    return mapRecommendation(
      await request("/api/recommend", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...payload, ...(force_refresh ? { force_refresh: true } : {}) }),
      }),
    );
  },
  feedback: (data) =>
    request("/api/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),
  generateInspiration: async ({ season, scene, referenceIds = [] }) => {
    const result = await request("/api/inspiration/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        season: seasonCode(season),
        scene,
        reference_ids: referenceIds,
      }),
    });
    if (Array.isArray(result.looks)) {
      return result.looks.map((look, index) => ({
        id: look.id || `look-${index + 1}`,
        title: look.title || `Look ${String(index + 1).padStart(2, "0")}`,
        subtitle: look.subtitle || `${season}季${scene}`,
        imageUrl: mediaUrl(look.image_url || look.imageUrl),
      }));
    }
    return [
      {
        id: "look-1",
        title: "Look 01 / New Direction",
        subtitle: `${season}季${scene}`,
        imageUrl: mediaUrl(result.image_url),
      },
    ];
  },
};
