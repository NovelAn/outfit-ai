export type ScreenId = 'today' | 'wardrobe' | 'inspiration' | 'archive' | 'profile';

export interface OutfitItem {
  id: string;
  brand: string;
  name: string;
  category: '上装' | '下装' | '鞋履' | '配饰';
  imageUrl: string;
  primaryColor?: string;
  secondaryColor?: string;
  material?: string;
  fit?: string;
  styles?: string[];
  tags?: string[];
  seasons?: string[];
  occasions?: string[];
  thickness?: string;
  isNew?: boolean;
}

export interface RecommendationCategory {
  id: string;
  title: string;
  tag: string;
  tagSub: string;
  editorialNo: string;
  itemsSummary: string;
  description: string;
  images: {
    top: string;
    bottom: string;
    shoes: string;
  };
  bgTone: string;
}

export interface InspirationItem {
  id: string;
  title: string;
  category: string;
  imageUrl: string;
  tags: string[];
  badge?: string;
  date?: string;
}

export interface GeneratedLook {
  id: string;
  title: string;
  imageUrl: string;
  subtitle: string;
}

export interface FavoriteLook {
  id: string;
  title: string;
  tag: string;
  imageUrl: string;
  dateAdded: string;
  type: 'look' | 'inspiration';
  description?: string;
  lookItems?: { name: string; category: string; img: string }[];
}

export interface HistoryLook {
  id: string;
  title: string;
  date: string;
  tag: string;
  imageUrl: string;
  description: string;
  items: { name: string; category: string; img: string }[];
  action?: string;
}

export interface LookRating {
  lookId: string;
  lookTitle: string;
  rating: number; // 1 to 5
  tags: string[];
  comment?: string;
  timestamp: string;
  aiAdjustment: string;
  lookImage?: string;
}

export interface AITasteProfile {
  totalRatingsCount: number;
  matchScore: number; // e.g. 96.8
  wardrobeItemCount: number;
  inspirationItemCount: number;
  preferredTags: string[];
  avoidedTags: string[];
}
