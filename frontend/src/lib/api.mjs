const API_BASE = (import.meta.env?.VITE_API_BASE_URL || "").replace(/\/$/, "");

const TIER_META = {
  safe: { title: "Look 01 / 稳妥 (SAFE)", tag: "日杂经典" },
  fresh: { title: "Look 02 / 新鲜 (FRESH)", tag: "松弛休假" },
  stretch: { title: "Look 03 / 突破 (STRETCH)", tag: "工装廓形" },
};

function apiUrl(path) {
  return `${API_BASE}${path}`;
}

async function request(path, options = {}) {
  const response = await fetch(apiUrl(path), options);
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
  return {
    id: item.id,
    brand: item.brand || "",
    name: item.name || "待确认单品",
    category: categoryLabel(item.category),
    imageUrl: mediaUrl(item.image_url),
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
    .slice(0, 3)
    .map((value) => `#${String(value).replace(/^#/, "")}`);
  const statusBadges = { pending: "等待中", analyzing: "分析中", failed: "处理失败" };
  return {
    id: reference.id,
    title: keywords[0] || "正在沉淀的灵感",
    category: keywords[0] || "Reference",
    imageUrl: mediaUrl(reference.image_url),
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
  };
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
  history: () => request("/api/history"),
  recommend: async (data) =>
    mapRecommendation(
      await request("/api/recommend", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      }),
    ),
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
    if (Array.isArray(result.looks) && result.looks.length > 0) {
      const looks = result.looks.map((look, index) => ({
        id: look.id || `look-${index + 1}`,
        title: look.title || `Look ${String(index + 1).padStart(2, "0")}`,
        subtitle: look.subtitle || `${season}季${scene}`,
        imageUrl: mediaUrl(look.image_url || look.imageUrl),
      }));
      return {
        looks,
        status: result.status || (looks.length === 3 ? "complete" : "partial"),
        requestedCount: result.requested_count || 3,
        generatedCount: result.generated_count || looks.length,
      };
    }
    throw new Error("灵感图生成结果为空，请稍后重试");
  },
};
