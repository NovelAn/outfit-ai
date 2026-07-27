import type {
  FeedbackAction,
  HistoryItem,
  Profile,
  Recommendation,
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
    if (typeof errMsg === "string") return errMsg;
  }
  return fallback;
}

function request<T>(
  path: string,
  method: NonNullable<UniApp.RequestOptions["method"]> | "PATCH" = "GET",
  data?: UniApp.RequestOptions["data"],
): Promise<T> {
  return new Promise((resolve, reject) => {
    uni.request({
      url: `${API_BASE}${path}`,
      method: method as UniApp.RequestOptions["method"],
      data,
      success: (response) => {
        if (response.statusCode >= 200 && response.statusCode < 300) {
          resolve(response.data as T);
        } else {
          reject(new Error(errorMessage(response.data, response.statusCode)));
        }
      },
      fail: (error) => reject(new Error(error.errMsg || "无法连接服务")),
    });
  });
}

export function mediaUrl(path: string | null | undefined): string {
  if (!path) return "";
  if (/^(https?:|data:|blob:)/.test(path)) return path;
  return `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;
}

export const api = {
  items: () => request<WardrobeItem[]>("/api/wardrobe/items"),
  itemStatus: (id: string) => request<WardrobeItem>(`/api/wardrobe/${id}/status`),
  updateItem: (id: string, data: Partial<WardrobeItem>) =>
    request<WardrobeItem>(`/api/wardrobe/${id}`, "PATCH", data),
  retryItem: (id: string) =>
    request<{ id: string; status: string }>(`/api/wardrobe/${id}/retry`, "POST"),
  profile: () => request<Profile>("/api/profile"),
  saveProfile: (profile: Profile) => request<Profile>("/api/profile", "PUT", profile),
  refreshTasteMemo: () => request<{ ok: boolean }>("/api/profile/taste-memo/refresh", "POST"),
  recommend: (data: {
    occasion: string;
    mood: string;
    city?: string;
    latitude?: number;
    longitude?: number;
    locked_item_ids: string[];
  }) => request<Recommendation>("/api/recommend", "POST", data),
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
      fail: (error) => reject(new Error(error.errMsg || "上传失败")),
    });
  });
}
