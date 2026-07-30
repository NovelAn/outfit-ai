import type {
  FeedbackAction,
  HistoryItem,
  InspirationResult,
  Profile,
  Recommendation,
  StyleReference,
  WardrobeItem,
} from "./types";

const API_BASE = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");

function errorMessage(data: unknown, statusCode: number): string {
  if (data && typeof data === "object" && "detail" in data) {
    const detail = (data as { detail?: unknown }).detail;
    if (typeof detail === "string") return detail;
  }
  return `请求失败（${statusCode}）`;
}

export function messageOf(cause: unknown, fallback = "操作失败，请稍后重试"): string {
  if (cause instanceof Error) return cause.message;
  if (cause && typeof cause === "object" && "errMsg" in cause) {
    const errMsg = (cause as { errMsg?: unknown }).errMsg;
    if (typeof errMsg === "string" && errMsg.includes("cancel")) return "cancel";
    if (typeof errMsg === "string" && !errMsg.startsWith("request:")) return errMsg;
  }
  return fallback;
}

function request<T>(
  path: string,
  method: UniApp.RequestOptions["method"] = "GET",
  data?: UniApp.RequestOptions["data"],
): Promise<T> {
  return new Promise((resolve, reject) => {
    uni.request({
      url: `${API_BASE}${path}`,
      method,
      data,
      success: (response) => {
        if (response.statusCode >= 200 && response.statusCode < 300) {
          resolve(response.data as T);
        } else {
          reject(new Error(errorMessage(response.data, response.statusCode)));
        }
      },
      fail: () => reject(new Error("无法连接造型服务，请检查网络后重试")),
    });
  });
}

export function mediaUrl(path: string | null | undefined): string {
  if (!path) return "";
  if (/^(https?:|data:|blob:|file:|wxfile:)/.test(path) || path.startsWith("/tmp/")) return path;
  return `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;
}

export const api = {
  items: () => request<WardrobeItem[]>("/api/wardrobe/items"),
  itemStatus: (id: string) => request<WardrobeItem>(`/api/wardrobe/${id}/status`),
  confirmItem: (id: string, data: Partial<WardrobeItem>) =>
    request<WardrobeItem>(`/api/wardrobe/${id}/confirm`, "POST", data),
  retryItem: (id: string) =>
    request<{ id: string; status: string }>(`/api/wardrobe/${id}/retry`, "POST"),
  profile: () => request<Profile>("/api/profile"),
  saveProfile: (profile: Profile) => request<Profile>("/api/profile", "PUT", profile),
  draftStyleDna: (profile: Profile) =>
    request<{ draft: Profile }>("/api/profile/style-dna/draft", "POST", profile),
  refreshTasteMemo: () => request<{ ok: boolean }>("/api/profile/taste-memo/refresh", "POST"),
  recommend: (data: {
    occasion: string;
    scene?: string;
    mood?: string;
    season?: "spring" | "summer" | "autumn" | "winter" | "spring_autumn";
    style_note?: string;
    reference_ids: string[];
    city?: string;
    latitude?: number;
    longitude?: number;
    locked_item_ids: string[];
  }) => request<Recommendation>("/api/recommend", "POST", data),
  styleReferences: () => request<StyleReference[]>("/api/style-references"),
  styleReferenceStatus: (id: string) =>
    request<StyleReference>(`/api/style-references/${id}/status`),
  retryStyleReference: (id: string) =>
    request<{ id: string; status: string }>(`/api/style-references/${id}/retry`, "POST"),
  generateInspiration: (data: {
    reference_ids: string[];
    style_note?: string;
    season?: "spring" | "summer" | "autumn" | "winter" | "spring_autumn";
    scene: string;
  }) => request<InspirationResult>("/api/inspiration/generate", "POST", data),
  feedback: (data: {
    history_id: string;
    items_worn: string[];
    action: FeedbackAction;
    occasion?: string;
    sentiment?: string;
  }) => request<{ ok: boolean }>("/api/feedback", "POST", data),
  history: () => request<HistoryItem[]>("/api/history"),
  collage: (ids: string[]) =>
    mediaUrl(`/api/wardrobe/collage?item_ids=${encodeURIComponent(ids.join(","))}`),
};

export function uploadItem(filePath: string): Promise<{ id: string; status: string }> {
  return new Promise((resolve, reject) => {
    uni.uploadFile({
      url: `${API_BASE}/api/wardrobe/upload`,
      filePath,
      name: "file",
      success: (response) => {
        let data: unknown;
        try {
          data = JSON.parse(response.data);
        } catch {
          reject(new Error("上传返回格式错误"));
          return;
        }
        if (response.statusCode >= 200 && response.statusCode < 300) {
          resolve(data as { id: string; status: string });
        } else {
          reject(new Error(errorMessage(data, response.statusCode)));
        }
      },
      fail: () => reject(new Error("无法连接造型服务，请检查网络后重试")),
    });
  });
}

export function uploadStyleReference(filePath: string): Promise<{ id: string; status: string }> {
  return new Promise((resolve, reject) => {
    uni.uploadFile({
      url: `${API_BASE}/api/style-references/upload`,
      filePath,
      name: "file",
      success: (response) => {
        let data: unknown;
        try {
          data = JSON.parse(response.data);
        } catch {
          reject(new Error("上传返回格式错误"));
          return;
        }
        if (response.statusCode >= 200 && response.statusCode < 300) {
          resolve(data as { id: string; status: string });
        } else {
          reject(new Error(errorMessage(data, response.statusCode)));
        }
      },
      fail: () => reject(new Error("无法连接造型服务，请检查网络后重试")),
    });
  });
}
