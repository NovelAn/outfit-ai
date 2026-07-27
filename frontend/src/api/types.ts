export type AnalysisStatus = "pending" | "analyzing" | "ready" | "failed";
export type PickMode = "safe" | "fresh" | "stretch";
export type FeedbackAction = "shown" | "saved" | "skipped" | "worn";

export interface WardrobeItem {
  id: string;
  name: string | null;
  category: string | null;
  primary_color: string | null;
  secondary_color?: string | null;
  material?: string | null;
  fit?: string | null;
  formality?: string | null;
  styles?: string[];
  tags?: string[];
  seasons?: string[];
  occasions?: string[];
  versatility?: number | null;
  brand?: string | null;
  size?: string | null;
  image_url: string;
  status: AnalysisStatus;
  attempt_count: number;
  confirmed_by_user: boolean;
}

export interface Profile {
  user_id: string;
  body: Record<string, unknown>;
  color_season: string | null;
  color_undertone: string | null;
  palette: string[];
  style_keywords: string[];
  avoids: string[];
  preferred_colors: string[];
  preferred_styles: string[];
  brand_sizes: Record<string, string>;
  city: string | null;
  climate: string | null;
  occasions: string[];
  taste_memo: string;
  taste_memo_updated_at?: string | null;
  feedback_since_refresh?: number;
}

export interface Weather {
  temp: number;
  feels_like: number;
  condition: string;
  humidity: number;
  wind_speed: number;
  is_daytime: boolean;
  temp_max: number;
  temp_min: number;
}

export interface RecommendationItem {
  id: string;
  name: string | null;
  category: string | null;
  image_url: string;
  primary_color: string | null;
}

export interface Look {
  history_id: string;
  items: RecommendationItem[];
  reason: string;
  weather_fit: string;
  occasion_fit: string;
  pick_mode: PickMode;
}

export interface Recommendation {
  weather: Weather;
  safe?: Look;
  fresh?: Look;
  stretch?: Look;
}

export interface HistoryItem {
  id: string;
  date: string;
  item_ids: string[];
  pick_mode: PickMode;
  occasion: string | null;
  mood: string | null;
  reason: string | null;
  collage_path?: string | null;
  action: FeedbackAction;
  wore_it: boolean;
}
