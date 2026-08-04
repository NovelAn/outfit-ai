import React, { useState, useEffect, useRef } from 'react';
import { ScreenId, LookRating, FavoriteLook } from '../types';
import { api, confirmFeedback } from '../lib/api.mjs';
import { loadDailyRecommendation, resolveLocationContext } from '../lib/location.mjs';
import { BottomNav } from './BottomNav';
import { SideDrawer } from './SideDrawer';

interface ScreenTodayProps {
  onNavigate: (screen: ScreenId) => void;
}

const FEEDBACK_TAG_OPTIONS = [
  '🎨 色彩搭配好',
  '📐 剪裁得体',
  '👔 过于正式',
  '☕ 缺松弛感',
  '🧥 想看叠穿',
  '🌿 偏好天然织物',
  '👟 想换休闲鞋'
];

const LOOK_VARIANTS: Record<string, Array<{
  title: string;
  tag: string;
  description: string;
  imageUrl: string;
  items: { name: string; category: string; img: string; desc: string }[];
}>> = {
  safe: [
    {
      title: 'Look 01 / 稳妥 (SAFE)',
      tag: '日杂经典',
      description: '全棉精纺白衬衫 + 藏青剪裁西裤 + 乐福鞋',
      imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuDFEJapTzg7M2pWwwrAPXMMImbFzrYpkWckOASqNeyP-hx0RuVCZMR_hOAczTSsxi88EKn-yAhj3v12qBClhH3X2JUBtmX-3No4Q3tHG7M_qgxJU3BpZ9Z7ux-iGduVDAShKM_VfHmG1WLA5irrPRU_a5ZMddYMH0sZvcH_Y93s-JrfJ-IU6IenJUxj29G4AEK2wyyihIgAnNwgsCmoYkHhoyU3q7kvlRPI7CA1as9nTSGeCo8728tJ',
      items: [
        { name: 'Classic White Shirt', category: '上装', img: 'https://lh3.googleusercontent.com/aida-public/AB6AXuDFEJapTzg7M2pWwwrAPXMMImbFzrYpkWckOASqNeyP-hx0RuVCZMR_hOAczTSsxi88EKn-yAhj3v12qBClhH3X2JUBtmX-3No4Q3tHG7M_qgxJU3BpZ9Z7ux-iGduVDAShKM_VfHmG1WLA5irrPRU_a5ZMddYMH0sZvcH_Y93s-JrfJ-IU6IenJUxj29G4AEK2wyyihIgAnNwgsCmoYkHhoyU3q7kvlRPI7CA1as9nTSGeCo8728tJ', desc: '全棉精纺白衬衫，挺括透气，职场与日常兼备。' },
        { name: 'Tailored Navy Trousers', category: '下装', img: 'https://lh3.googleusercontent.com/aida-public/AB6AXuAPNznerXhWs_PBUIjy3_5VGM9WlIxCkDTAU0iMqDgtdZej0uNDXIWLdKBvxcJgxLc2IsrtDgnYxWrMvf1Fr_ZFBHxCIzJHEnDVMa8qkZlKkzdPZrTGYECrSnYw0-Q9jfu1OGlWfAZyZPc_m32DFLTZnpFwa02TamNqOy3Qb87tIJ1m8NT-Hh47d3ri26OPD_OmaqmpSt7jub6jiJ94eisU4gnGwxQbEI6eSo0jTAFU0VA6YU6KjHHB', desc: '藏青色剪裁西裤，微锥廓形，提升整体干练气质。' },
        { name: 'Brown Leather Loafers', category: '鞋履', img: 'https://lh3.googleusercontent.com/aida-public/AB6AXuAN-vdwTEbVAujzyoBX7uIMHV9bkCM_LXhzfKJcXTYcfLA5h7rIDCmaV6Pj98BAaCjURMJR-fgUe3chDKgbCCbWQzw5ElvQS2MwBej4bX2ZkNNyeD8xji_miQIM1jzaMTpRxHiCbKoTe9V524eAGMU1I7ddUgdDbkATGdQFuNS7oLHEITmf289th8ZJkbDCU_tibwfu9ft0F5vCqk9D6LtJsP2tVyp4p9Ae1c4bzyVqlSLRLmAJZQXr', desc: '复古棕色乐福鞋，软牛皮材质，复古舒适。' }
      ]
    },
    {
      title: 'Look 01 / 稳妥 (SAFE Alt)',
      tag: '高级通勤',
      description: '燕麦色高密针织衫 + 炭灰垂坠西裤 + 漆皮德比鞋',
      imageUrl: 'https://images.unsplash.com/photo-1576995853123-5a10305d93c0?w=500&auto=format&fit=crop&q=80',
      items: [
        { name: 'Oatmeal Knit Sweater', category: '上装', img: 'https://images.unsplash.com/photo-1576995853123-5a10305d93c0?w=300&auto=format&fit=crop&q=80', desc: '燕麦色高密重磅针织衫，手感亲肤，展现内敛质感。' },
        { name: 'Charcoal Pleated Pants', category: '下装', img: 'https://images.unsplash.com/photo-1594633312681-425c7b97ccd1?w=300&auto=format&fit=crop&q=80', desc: '炭灰色双褶垂坠西裤，流线裁剪，从容百搭。' },
        { name: 'Black Patent Oxfords', category: '鞋履', img: 'https://images.unsplash.com/photo-1533867617858-e7b97e060509?w=300&auto=format&fit=crop&q=80', desc: '黑色微光泽皮鞋，修饰脚型，通勤得体。' }
      ]
    },
    {
      title: 'Look 01 / 稳妥 (SAFE V3)',
      tag: '干练商务',
      description: '浅蓝牛津纺衬衫 + 深卡其修身直筒裤 + 复古便鞋',
      imageUrl: 'https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?w=500&auto=format&fit=crop&q=80',
      items: [
        { name: 'Light Blue Oxford Shirt', category: '上装', img: 'https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?w=300&auto=format&fit=crop&q=80', desc: '经典浅蓝牛津纺衬衫，质感扎实，日常不踩雷。' },
        { name: 'Deep Khaki Chinos', category: '下装', img: 'https://images.unsplash.com/photo-1473966968600-fa801b869a1a?w=300&auto=format&fit=crop&q=80', desc: '深卡其高密斜纹长裤，修身挺括。' },
        { name: 'Vintage Leather Slip-ons', category: '鞋履', img: 'https://images.unsplash.com/photo-1549298916-b41d501d3772?w=300&auto=format&fit=crop&q=80', desc: '经典复古皮质便鞋，轻便优雅。' }
      ]
    }
  ],
  fresh: [
    {
      title: 'Look 02 / 新鲜 (FRESH)',
      tag: '松弛休假',
      description: '蓝白条纹衬衫 + 米色斜纹裤 + 德训小白鞋',
      imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuCHxxA9TF55gxJT7Guqb18Wfu94ote5YoOVoiOJhoRQYcplRQBhb7aUmcHkl5_sbSbZvBGRN5Hmlnk6N7L7A58H7jb5ASvriWyvc9Gp9efDZ8M05YMdF2GQ079oj50pyhGPIRg_EJrSbJJhs3EWLJOz9lfvlXZbQMe2f0ZPiXX_vN5aKJ7OIx97fZSLYjGUTMPxPoGvl7eDUBAEVv_-nGfiOMENaf_v-D13cDyTxvI3ifa8oe0SxF8F',
      items: [
        { name: 'Striped Poplin Shirt', category: '上装', img: 'https://lh3.googleusercontent.com/aida-public/AB6AXuCHxxA9TF55gxJT7Guqb18Wfu94ote5YoOVoiOJhoRQYcplRQBhb7aUmcHkl5_sbSbZvBGRN5Hmlnk6N7L7A58H7jb5ASvriWyvc9Gp9efDZ8M05YMdF2GQ079oj50pyhGPIRg_EJrSbJJhs3EWLJOz9lfvlXZbQMe2f0ZPiXX_vN5aKJ7OIx97fZSLYjGUTMPxPoGvl7eDUBAEVv_-nGfiOMENaf_v-D13cDyTxvI3ifa8oe0SxF8F', desc: '蓝白细条纹府绸衬衫，清爽怡人，透出日杂轻松质感。' },
        { name: 'Wide Beige Chinos', category: '下装', img: 'https://lh3.googleusercontent.com/aida-public/AB6AXuCrvUXxvthYe4iduUJxWY5SvIOM3sVuJFeZ1eWoymxCdO_cUOHfHK6ZukP__qhUm-ktQdwL13vMBqq8pnttopmY82fkud_HzQ6aPBIFcBErmzDBzmYT4Ta2IVufaZhtNTB1b2htO5cRRJBppvdPJvGYAPDlMuqeTOLyGPEv6WpQ1Jnad8CPkiLbKJz-B_WHeddi-WexZ904cyui2iB9RpZD1tMkPuekWnatWeNJQNbnGlvbE92JslH4', desc: '米色宽松斜纹裤，适度落坠感，轻松营造城市休假氛围。' },
        { name: 'Minimal German Trainer', category: '鞋履', img: 'https://lh3.googleusercontent.com/aida-public/AB6AXuD1vLgHCQs2fd6VwanjCEfaOHNvq4zTuLHSVz5JJ0w0Fhnx-wskEWbi9V7-OFpzEEFkFe4USssjMrNmRL-qXmJ6iJlQqael0aQGKJezRyijDx9ttARLRXk5H1AcZN5Doew3K2VsG9Jg_yrXxwzxY5rZa0yaPRSPDjbIqO-mU9dfhkkUL6MSLz5xFvoxbrVcWhFNEWz9WDXS7WmUELKS8zUfLXA3odjQRjAnitNN9379Pf7_MMe23NAt', desc: '极简白色德训鞋/小白鞋，舒适平底，提升造型清爽度。' }
      ]
    },
    {
      title: 'Look 02 / 新鲜 (FRESH Alt)',
      tag: '清爽古巴领',
      description: '薄荷绿棉麻短袖衬衫 + 水洗浅蓝牛仔长裤 + 编织凉鞋',
      imageUrl: 'https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=500&auto=format&fit=crop&q=80',
      items: [
        { name: 'Mint Linen Camp Shirt', category: '上装', img: 'https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=300&auto=format&fit=crop&q=80', desc: '薄荷绿棉麻古巴领短袖衬衫，透气凉爽。' },
        { name: 'Washed Light Blue Denim', category: '下装', img: 'https://images.unsplash.com/photo-1541099649105-f69ad21f3246?w=300&auto=format&fit=crop&q=80', desc: '浅复古水洗牛仔裤，营造夏日空气感。' },
        { name: 'Leather Woven Sandals', category: '鞋履', img: 'https://images.unsplash.com/photo-1603808033192-082d6919d3e1?w=300&auto=format&fit=crop&q=80', desc: '手作皮革编织凉鞋，随意慵懒。' }
      ]
    }
  ],
  stretch: [
    {
      title: 'Look 03 / 突破 (STRETCH)',
      tag: '工装廓形',
      description: '橄榄绿无结构西装 + 黑色工装裤 + 厚底德比鞋',
      imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuB9zc4UnQuZ3eYOMp1SlgcMTx5GDWw5FJK10oRRxpGWCuwq3FiKm2waRVfrM-0uant5SbFTO2YG7DRog2z_J7sR2yWBKiMZftRXOfEeG_8PKjtVe6sP_Mbupoui5qF0lLguKCsQVKAgR-UiqSTBbMFTVB3loUSKfVC_SAoH_eTx4AeOm7Yn7u-KLIfadj16dH8E9rkPP2uXl60Hc51AOCUSyNN2SENNUrp_E0-1_Hk7a4fYzg4cWR1H',
      items: [
        { name: 'Unstructured Olive Blazer', category: '上装', img: 'https://lh3.googleusercontent.com/aida-public/AB6AXuB9zc4UnQuZ3eYOMp1SlgcMTx5GDWw5FJK10oRRxpGWCuwq3FiKm2waRVfrM-0uant5SbFTO2YG7DRog2z_J7sR2yWBKiMZftRXOfEeG_8PKjtVe6sP_Mbupoui5qF0lLguKCsQVKAgR-UiqSTBbMFTVB3loUSKfVC_SAoH_eTx4AeOm7Yn7u-KLIfadj16dH8E9rkPP2uXl60Hc51AOCUSyNN2SENNUrp_E0-1_Hk7a4fYzg4cWR1H', desc: '橄榄绿无结构休闲西装，慵懒工装风格，独具个性。' },
        { name: 'Technical Black Cargos', category: '下装', img: 'https://lh3.googleusercontent.com/aida-public/AB6AXuAqpYFVWUzfw-4ksJpBLdJdVwN1xqkElYLCgCOx4u11eQA5DBylOG5hqSOaJwUjnEWh41t973ciX6Wq1iW5cYeebbEmD9uGGqvOXHjIhffF5_k5_Cv1u5zdvTJ95BGVH4iw6uYQZ14VMWYSvrgD_vm2f9sbv5nZg-X9mrya8vR10UHqN2-n4lLUbR80ipn8pqxAsqOSEiSr7rAHzadqI4QeOxtE0wKpwidj3YOOSinzeLDnu2MtC3bt', desc: '黑色机能工装裤，机能风口袋设计，塑造硬朗前卫轮廓。' },
        { name: 'Chunky Leather Derbies', category: '鞋履', img: 'https://lh3.googleusercontent.com/aida-public/AB6AXuCLXluygCqK47peeLl2k8_klHFPVVzzqZll7YJVmDtT4_qOAJRUBmCSArhFElCfC6XlMxSnPMMYMIkrdhqDwIyiAgRaoKWq20xDOt5NE8Gt62Y5H1jd0qNqT-exJmyd7fazCTKtpKxo2QMTuv_9Wc9f6wgAgPaI3d2d7eubA42j0mkztyhoHQlvM1Q4lHZV_hu5dlwgWZi-nyHfcJLYrsraiIJziKJNmXOxDczT-GGXW-Vyg7mjXaQv', desc: '厚底皮质德比鞋，重磅量感底座，打破传统仪式感。' }
      ]
    },
    {
      title: 'Look 03 / 突破 (STRETCH Alt)',
      tag: '复古猎装',
      description: '麂皮质感短款夹克 + 军绿束脚工装裤 + 重磅高帮马丁靴',
      imageUrl: 'https://images.unsplash.com/photo-1551028719-00167b16eac5?w=500&auto=format&fit=crop&q=80',
      items: [
        { name: 'Suede Utility Jacket', category: '上装', img: 'https://images.unsplash.com/photo-1551028719-00167b16eac5?w=300&auto=format&fit=crop&q=80', desc: '麂皮质感短款猎装夹克，质感复古惊艳。' },
        { name: 'Army Green Joggers', category: '下装', img: 'https://images.unsplash.com/photo-1517445312882-bc9910d016b7?w=300&auto=format&fit=crop&q=80', desc: '军绿色立体剪裁工装裤。' },
        { name: 'Chunky Boots', category: '鞋履', img: 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=300&auto=format&fit=crop&q=80', desc: '重磅量感高帮马丁靴。' }
      ]
    }
  ]
};

const LOOK_DETAILS: Record<string, FavoriteLook> = {
  safe: {
    id: 'safe',
    title: 'Look 01 / 稳妥 (SAFE)',
    tag: '日杂经典',
    imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuDFEJapTzg7M2pWwwrAPXMMImbFzrYpkWckOASqNeyP-hx0RuVCZMR_hOAczTSsxi88EKn-yAhj3v12qBClhH3X2JUBtmX-3No4Q3tHG7M_qgxJU3BpZ9Z7ux-iGduVDAShKM_VfHmG1WLA5irrPRU_a5ZMddYMH0sZvcH_Y93s-JrfJ-IU6IenJUxj29G4AEK2wyyihIgAnNwgsCmoYkHhoyU3q7kvlRPI7CA1as9nTSGeCo8728tJ',
    dateAdded: '今日推荐',
    type: 'look',
    description: '全棉精纺白衬衫 + 藏青剪裁西裤 + 乐福鞋',
    lookItems: LOOK_VARIANTS.safe[0].items
  },
  fresh: {
    id: 'fresh',
    title: 'Look 02 / 新鲜 (FRESH)',
    tag: '松弛休假',
    imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuCHxxA9TF55gxJT7Guqb18Wfu94ote5YoOVoiOJhoRQYcplRQBhb7aUmcHkl5_sbSbZvBGRN5Hmlnk6N7L7A58H7jb5ASvriWyvc9Gp9efDZ8M05YMdF2GQ079oj50pyhGPIRg_EJrSbJJhs3EWLJOz9lfvlXZbQMe2f0ZPiXX_vN5aKJ7OIx97fZSLYjGUTMPxPoGvl7eDUBAEVv_-nGfiOMENaf_v-D13cDyTxvI3ifa8oe0SxF8F',
    dateAdded: '今日推荐',
    type: 'look',
    description: '蓝白条纹衬衫 + 米色斜纹裤 + 德训小白鞋',
    lookItems: LOOK_VARIANTS.fresh[0].items
  },
  stretch: {
    id: 'stretch',
    title: 'Look 03 / 突破 (STRETCH)',
    tag: '工装廓形',
    imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuB9zc4UnQuZ3eYOMp1SlgcMTx5GDWw5FJK10oRRxpGWCuwq3FiKm2waRVfrM-0uant5SbFTO2YG7DRog2z_J7sR2yWBKiMZftRXOfEeG_8PKjtVe6sP_Mbupoui5qF0lLguKCsQVKAgR-UiqSTBbMFTVB3loUSKfVC_SAoH_eTx4AeOm7Yn7u-KLIfadj16dH8E9rkPP2uXl60Hc51AOCUSyNN2SENNUrp_E0-1_Hk7a4fYzg4cWR1H',
    dateAdded: '今日推荐',
    type: 'look',
    description: '橄榄绿无结构西装 + 黑色工装裤 + 厚底德比鞋',
    lookItems: LOOK_VARIANTS.stretch[0].items
  }
};

const EMPTY_ITEMS = ['上装', '下装', '鞋履'].map((category) => ({
  name: '尚未生成',
  category,
  img: 'data:image/gif;base64,R0lGODlhAQABAAD/ACwAAAAAAQABAAACADs=',
  desc: '先在衣橱确认真实单品，再点击 AI 换一换。',
}));

const EMPTY_LOOKS: Record<'safe' | 'fresh' | 'stretch', any> = {
  safe: { title: 'Look 01 / 稳妥 (SAFE)', tag: '日杂经典', description: '等待从真实衣橱生成', imageUrl: '', items: EMPTY_ITEMS },
  fresh: { title: 'Look 02 / 新鲜 (FRESH)', tag: '松弛休假', description: '等待从真实衣橱生成', imageUrl: '', items: EMPTY_ITEMS },
  stretch: { title: 'Look 03 / 突破 (STRETCH)', tag: '工装廓形', description: '等待从真实衣橱生成', imageUrl: '', items: EMPTY_ITEMS },
};

const LookItems = ({ items = [], onSelect }: { items: any[]; onSelect: (item: any) => void }) => (
  <div className="grid w-full grid-cols-3 gap-2">
    {items.map((item, index) => (
      <button
        key={item.id || `${item.name}-${index}`}
        onClick={() => onSelect(item)}
        className="aspect-square overflow-hidden rounded-lg border border-[#c4c6cd]/40 bg-white p-1.5 hover:border-[#9a442a]/50 transition-colors"
      >
        <img className="h-full w-full object-contain" src={item.img} alt={item.name} />
        <span className="sr-only">{item.name}</span>
      </button>
    ))}
  </div>
);

export const ScreenToday: React.FC<ScreenTodayProps> = ({ onNavigate }) => {
  const [liked, setLiked] = useState<Record<string, boolean>>({});
  const [activeModalItem, setActiveModalItem] = useState<{ title: string; desc: string } | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [locationContext, setLocationContext] = useState<any>({ source: 'missing' });
  const locationRef = useRef<any>({ source: 'missing' });
  const [weather, setWeather] = useState<any>(null);
  const [weatherIsStale, setWeatherIsStale] = useState(false);
  const weatherRef = useRef<any>(null);
  const dailyRefreshRef = useRef<Promise<any> | null>(null);
  const recommendationRequestRef = useRef(0);
  const swapInFlightRef = useRef(false);
  const [liveLooks, setLiveLooks] = useState<any>(() => {
    try {
      const cached = localStorage.getItem('OUTFIT_AI_LATEST_RECOMMENDATION');
      return cached ? JSON.parse(cached) : null;
    } catch {
      return null;
    }
  });

  // Rating & Swap states per look
  const [ratings, setRatings] = useState<Record<string, LookRating>>({});
  const [variantsIdx, setVariantsIdx] = useState<Record<string, number>>({
    safe: 0,
    fresh: 0,
    stretch: 0
  });
  const [swappingTier, setSwappingTier] = useState<string | null>(null);

  // Comparison Mode states
  const [isCompareMode, setIsCompareMode] = useState<boolean>(false);
  const [selectedCompareKeys, setSelectedCompareKeys] = useState<('safe' | 'fresh' | 'stretch')[]>(['safe', 'fresh']);
  const [isCompareModalOpen, setIsCompareModalOpen] = useState<boolean>(false);

  const toggleCompareKey = (key: 'safe' | 'fresh' | 'stretch') => {
    if (selectedCompareKeys.includes(key)) {
      if (selectedCompareKeys.length <= 1) {
        triggerToast('请至少选择 1 套 Look 进行对比');
        return;
      }
      setSelectedCompareKeys(selectedCompareKeys.filter((k) => k !== key));
    } else {
      if (selectedCompareKeys.length >= 2) {
        setSelectedCompareKeys([selectedCompareKeys[1], key]);
      } else {
        setSelectedCompareKeys([...selectedCompareKeys, key]);
      }
    }
  };

  const getLookData = (key: 'safe' | 'fresh' | 'stretch') => {
    const variant = liveLooks?.[key] || EMPTY_LOOKS[key];
    return {
      key,
      title: variant.title,
      tag: variant.tag,
      tierName: key === 'safe' ? '稳妥 (SAFE)' : key === 'fresh' ? '新鲜 (FRESH)' : '突破 (STRETCH)',
      description: variant.description,
      imageUrl: variant.imageUrl,
      items: variant.items
    };
  };

  const getAIComparisonAnalysis = (keyA: 'safe' | 'fresh' | 'stretch', keyB: 'safe' | 'fresh' | 'stretch') => {
    const lookA = getLookData(keyA);
    const lookB = getLookData(keyB);

    let formalityA = 85;
    let formalityB = 45;
    let relaxA = 55;
    let relaxB = 90;
    let summary = '';
    let highlightA = '';
    let highlightB = '';
    let occasionAdvice = '';

    if ((keyA === 'safe' && keyB === 'fresh') || (keyA === 'fresh' && keyB === 'safe')) {
      formalityA = keyA === 'safe' ? 85 : 45;
      formalityB = keyB === 'safe' ? 85 : 45;
      relaxA = keyA === 'safe' ? 55 : 90;
      relaxB = keyB === 'safe' ? 55 : 90;
      summary = '“稳妥”与“新鲜”体现了从严谨精纺商务到呼吸感日杂休假的风格跨越。';
      highlightA = keyA === 'safe' ? '【稳妥】洁白精纺衬衫+藏青西裤，呈现利落权威感' : '【新鲜】蓝白细条纹+米色斜纹裤，透出空气感与亲和力';
      highlightB = keyB === 'safe' ? '【稳妥】洁白精纺衬衫+藏青西裤，呈现利落权威感' : '【新鲜】蓝白细条纹+米色斜纹裤，透出空气感与亲和力';
      occasionAdvice = '高层会议、重要商务拜访选【稳妥】；日常办公、下午茶咖啡或周末街拍选【新鲜】。';
    } else if ((keyA === 'safe' && keyB === 'stretch') || (keyA === 'stretch' && keyB === 'safe')) {
      formalityA = keyA === 'safe' ? 85 : 65;
      formalityB = keyB === 'safe' ? 85 : 65;
      relaxA = keyA === 'safe' ? 55 : 75;
      relaxB = keyB === 'safe' ? 55 : 75;
      summary = '“稳妥”是经典不踩雷的安全牌，“突破”则引入工装无结构轮廓与潮酷张力。';
      highlightA = keyA === 'safe' ? '【稳妥】标准日杂商务模板，剪裁工整得体' : '【突破】橄榄绿无结构外套+厚底德比鞋，先锋有态度';
      highlightB = keyB === 'safe' ? '【稳妥】标准日杂商务模板，剪裁工整得体' : '【突破】橄榄绿无结构外套+厚底德比鞋，先锋有态度';
      occasionAdvice = '追求专业稳重选【稳妥】；参观设计展、艺术街区巡游或夜间聚会选【突破】。';
    } else {
      formalityA = keyA === 'fresh' ? 45 : 65;
      formalityB = keyB === 'fresh' ? 45 : 65;
      relaxA = keyA === 'fresh' ? 90 : 75;
      relaxB = keyB === 'fresh' ? 90 : 75;
      summary = '“新鲜”主打轻盈随性与柔和亲和，“突破”突出工装廓形与硬朗质感。';
      highlightA = keyA === 'fresh' ? '【新鲜】浅色淡雅调性，极简德训鞋轻松百搭' : '【突破】立体机能工装口袋+厚底德比鞋，气场独立';
      highlightB = keyB === 'fresh' ? '【新鲜】浅色淡雅调性，极简德训鞋轻松百搭' : '【突破】立体机能工装口袋+厚底德比鞋，气场独立';
      occasionAdvice = '喜欢日系温和松弛氛围选【新鲜】；追求有范儿、个性鲜明潮流表达选【突破】。';
    }

    return {
      lookA,
      lookB,
      formalityA,
      formalityB,
      relaxA,
      relaxB,
      summary,
      highlightA,
      highlightB,
      occasionAdvice
    };
  };

  const [activeRatingModal, setActiveRatingModal] = useState<{ id: string; title: string; imageUrl?: string } | null>(null);
  const [currentStars, setCurrentStars] = useState<number>(5);
  const [selectedTags, setSelectedTags] = useState<string[]>(['🎨 色彩搭配好']);
  const [commentText, setCommentText] = useState<string>('');
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const applyRecommendation = (recommendation: any) => {
    setLiveLooks(recommendation);
    localStorage.setItem('OUTFIT_AI_LATEST_RECOMMENDATION', JSON.stringify(recommendation));
    if (recommendation.weather) {
      setWeather(recommendation.weather);
      weatherRef.current = recommendation.weather;
    }
    setWeatherIsStale(false);
    (['safe', 'fresh', 'stretch'] as const).forEach((key) => {
      const look = recommendation[key];
      LOOK_DETAILS[key] = {
        id: key,
        title: look.title,
        tag: look.tag,
        imageUrl: look.imageUrl,
        dateAdded: '今日推荐',
        type: 'look',
        description: look.description,
        lookItems: look.items,
      };
    });
  };

  const refreshDailyContext = () => {
    if (dailyRefreshRef.current) return dailyRefreshRef.current;
    const requestId = ++recommendationRequestRef.current;
    const task = (async () => {
      const context = await resolveLocationContext({ storage: localStorage });
      setLocationContext(context);
      locationRef.current = context;
      if (context.source === 'missing') {
        setWeatherIsStale(Boolean(weatherRef.current));
        return;
      }
      let latestWeather = weatherRef.current;
      try {
        latestWeather = await api.weather(context);
        setWeather(latestWeather);
        weatherRef.current = latestWeather;
        setWeatherIsStale(false);
      } catch {
        setWeatherIsStale(Boolean(weatherRef.current));
      }
      try {
        const recommendation = await loadDailyRecommendation({
          api,
          context,
          weather: latestWeather,
        });
        if (requestId === recommendationRequestRef.current) applyRecommendation(recommendation);
      } catch (error) {
        if (requestId === recommendationRequestRef.current && !liveLooks) {
          triggerToast(error instanceof Error ? error.message : '每日推荐加载失败');
        }
      }
    })();
    const tracked = task.finally(() => {
      if (dailyRefreshRef.current === tracked) dailyRefreshRef.current = null;
    });
    dailyRefreshRef.current = tracked;
    return tracked;
  };

  const handleSwapLook = async (tier: 'safe' | 'fresh' | 'stretch') => {
    if (swapInFlightRef.current) return;
    swapInFlightRef.current = true;
    setSwappingTier(tier);
    try {
      if (dailyRefreshRef.current) await dailyRefreshRef.current;
      const currentContext = locationRef.current;
      if (currentContext.source === 'missing') {
        triggerToast('需要定位或选择城市');
        return;
      }
      ++recommendationRequestRef.current;
      const recommendation = await loadDailyRecommendation({
        api,
        context: currentContext,
        weather: weatherRef.current || weather,
        forceRefresh: true,
      });
      applyRecommendation(recommendation);
      triggerToast('✨ AI 已根据真实衣橱与 Style DNA 生成三套新搭配！');
    } catch (error) {
      triggerToast(error instanceof Error ? error.message : '推荐生成失败');
    } finally {
      swapInFlightRef.current = false;
      setSwappingTier(null);
    }
  };

  const loadFavorites = () => {
    try {
      const favsStr = localStorage.getItem('OUTFIT_AI_FAVORITES');
      if (favsStr) {
        const favs: FavoriteLook[] = JSON.parse(favsStr);
        const likedMap: Record<string, boolean> = {};
        favs.forEach((f) => {
          likedMap[f.id] = true;
        });
        setLiked(likedMap);
      }

    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    try {
      const saved = localStorage.getItem('OUTFIT_AI_LOOK_RATINGS');
      if (saved) {
        setRatings(JSON.parse(saved));
      }
      loadFavorites();
      void refreshDailyContext();

      const handleStorageChange = () => {
        loadFavorites();
        void refreshDailyContext();
      };
      window.addEventListener('storage', handleStorageChange);
      return () => window.removeEventListener('storage', handleStorageChange);
    } catch (e) {
      console.error(e);
    }
  }, []);

  const triggerToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  const locationLabel = weather
    ? `${weather.city || locationContext.city || '当前地点'} / ${Math.round(weather.temp)}°C · ${weather.condition}`
    : locationContext.source === 'missing'
      ? '需要定位或选择城市'
      : '正在获取天气';
  const rainSummary = weather?.rain_window
    ? `降雨时段 ${weather.rain_window}`
    : weather
      ? `降雨概率 ${weather.precipitation_probability_max ?? 0}%${weather.precipitation_sum ? ` · ${weather.precipitation_sum} mm` : ''}`
      : '';

  const toggleLike = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!liveLooks?.[id]) {
      triggerToast('请先用真实衣橱生成搭配');
      return;
    }
    const isNowLiked = !liked[id];
    const look = liveLooks[id];

    try {
      const favsStr = localStorage.getItem('OUTFIT_AI_FAVORITES');
      let favs: FavoriteLook[] = favsStr ? JSON.parse(favsStr) : [];

      const commit = () => {
        if (isNowLiked) {
          const detail = { ...LOOK_DETAILS[id], id: look.historyId || id, historyId: look.historyId, lookItems: look.items };
          if (detail && !favs.some((f) => f.id === detail.id)) favs.unshift(detail);
          triggerToast('❤️ 已成功保存至【我的收藏】！');
        } else {
          favs = favs.filter((f) => f.id !== (look.historyId || id));
          triggerToast('已从【我的收藏】中移除');
        }
        setLiked((prev) => ({ ...prev, [id]: isNowLiked }));
        localStorage.setItem('OUTFIT_AI_FAVORITES', JSON.stringify(favs));
      };
      if (look.historyId) {
        await confirmFeedback(api.feedback, {
          history_id: look.historyId,
          items_worn: look.items.map((item: any) => item.id),
          action: isNowLiked ? 'saved' : 'shown',
        }, commit, (error: unknown) => {
          triggerToast(error instanceof Error ? error.message : '收藏状态同步失败');
        });
      } else {
        commit();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const openRatingModal = (id: string, title: string, imageUrl?: string) => {
    const existing = ratings[id];
    if (existing) {
      setCurrentStars(existing.rating);
      setSelectedTags(existing.tags || []);
      setCommentText(existing.comment || '');
    } else {
      setCurrentStars(5);
      setSelectedTags(['🎨 色彩搭配好']);
      setCommentText('');
    }
    setActiveRatingModal({ id, title, imageUrl });
  };

  const handleTagToggle = (tag: string) => {
    if (selectedTags.includes(tag)) {
      setSelectedTags(selectedTags.filter(t => t !== tag));
    } else {
      setSelectedTags([...selectedTags, tag]);
    }
  };

  const submitRating = async () => {
    if (!activeRatingModal) return;

    const id = activeRatingModal.id;
    const lookTitle = activeRatingModal.title;

    let aiAdjustment = '已优化款式推荐权重';
    if (selectedTags.includes('👔 过于正式') || selectedTags.includes('☕ 缺松弛感')) {
      aiAdjustment = '已调高【松弛休假风】权重 +15%，减少工整正装推荐';
    } else if (selectedTags.includes('🧥 想看叠穿')) {
      aiAdjustment = '已新增【秋冬质感叠穿】层次构图指导';
    } else if (selectedTags.includes('🌿 偏好天然织物')) {
      aiAdjustment = '已将【棉麻与天然羊毛】列为优先提取面料';
    } else {
      aiAdjustment = '已将此类精纺干练配色沉淀至你的核心品味 DNA';
    }

    const newRating: LookRating = {
      lookId: id,
      lookTitle,
      rating: currentStars,
      tags: selectedTags,
      comment: commentText,
      timestamp: new Date().toLocaleDateString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }),
      aiAdjustment,
      lookImage: activeRatingModal.imageUrl
    };

    const tier = id.split('-')[0];
    const look = liveLooks?.[tier];
    newRating.historyId = look?.historyId;
    newRating.lookItems = look?.items;
    const commit = () => {
      const updated = { ...ratings, [id]: newRating };
      setRatings(updated);
      localStorage.setItem('OUTFIT_AI_LOOK_RATINGS', JSON.stringify(updated));
      setActiveRatingModal(null);
      triggerToast(`✨ AI 基因库已吸收你的评价！${aiAdjustment}`);
    };
    if (look?.historyId) {
      try {
        await confirmFeedback(api.feedback, {
        history_id: look.historyId,
        items_worn: look.items.map((item: any) => item.id),
        rating: currentStars,
        sentiment: commentText || `${currentStars} 星`,
        compliments: selectedTags,
        }, commit, (error: unknown) => {
        triggerToast(error instanceof Error ? error.message : '反馈同步失败');
        });
      } catch {
        return;
      }
    } else {
      commit();
    }
  };

  return (
    <div className="min-h-screen bg-[#fbf9f4] text-[#1b1c19] pb-[100px]">
      {/* Side Drawer Menu */}
      <SideDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        currentScreen="today"
        onNavigate={onNavigate}
        locationLabel={locationLabel}
      />

      {/* Header */}
      <header className="sticky top-0 z-40 bg-[#fbf9f4]/95 backdrop-blur-md px-6 py-4 flex flex-col items-center border-b border-[#e4e2dd]">
        <div className="w-full flex flex-col gap-1 max-w-md mx-auto">
          <div className="flex items-center justify-between w-full">
            <div className="flex items-center gap-4">
              <button
                onClick={() => setIsDrawerOpen(true)}
                className="p-1 rounded hover:bg-[#f0eee9] text-[#162839] transition-colors"
                title="打开导航菜单"
              >
                <span className="material-symbols-outlined text-2xl block">menu</span>
              </button>
              <div className="flex flex-col">
                <span className="font-semibold text-[10px] tracking-widest text-[#43474c]">{locationLabel}</span>
                <span className="font-semibold text-[10px] uppercase tracking-widest text-[#43474c]">
                  {weather ? `${weather.local_date} · ${rainSummary}${weatherIsStale ? ' · 上次更新' : ''}` : ''}
                </span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => onNavigate('archive')}
                className="p-1 rounded hover:bg-[#f0eee9] text-[#162839] transition-colors"
                title="灵感搜索"
              >
                <span className="material-symbols-outlined text-xl block">search</span>
              </button>
            </div>
          </div>
          <div className="h-px bg-[#c4c6cd]/30 w-full mt-2"></div>
          <div className="flex items-center justify-between mt-2 font-semibold">
            <h1 className="font-serif-display text-[20px] sm:text-[22px] text-[#162839] tracking-tight font-semibold flex items-center gap-1">
              今日推荐 <span className="font-normal opacity-50 text-xs sm:text-sm">Daily Picks</span>
            </h1>
            <button
              onClick={() => {
                const nextMode = !isCompareMode;
                setIsCompareMode(nextMode);
                if (nextMode && selectedCompareKeys.length < 2) {
                  setSelectedCompareKeys(['safe', 'fresh']);
                }
              }}
              className={`text-xs font-bold px-3 py-1 rounded-full border transition-all flex items-center gap-1 shadow-2xs ${
                isCompareMode
                  ? 'bg-[#162839] text-white border-[#162839]'
                  : 'bg-white text-[#162839] border-[#162839]/40 hover:bg-[#162839]/10'
              }`}
            >
              <span className="material-symbols-outlined text-sm">compare_arrows</span>
              {isCompareMode ? '退出对比' : '对比模式'}
            </button>
          </div>

          {/* Comparison Banner when Comparison Mode is active */}
          {isCompareMode && (
            <div className="mt-3 bg-[#162839]/5 border border-[#162839]/20 rounded-xl p-2.5 flex flex-col gap-2 shadow-2xs animate-fade-in">
              <div className="flex items-center justify-between text-xs text-[#162839]">
                <div className="flex items-center gap-1 font-bold text-[11px]">
                  <span className="material-symbols-outlined text-sm text-[#9a442a]">compare_arrows</span>
                  <span>对比模式 ({selectedCompareKeys.length}/2)</span>
                </div>
                <div className="flex gap-1">
                  {(['safe', 'fresh', 'stretch'] as const).map((k) => {
                    const isSel = selectedCompareKeys.includes(k);
                    const name = k === 'safe' ? '稳妥' : k === 'fresh' ? '新鲜' : '突破';
                    return (
                      <button
                        key={k}
                        onClick={() => toggleCompareKey(k)}
                        className={`text-[10px] px-2 py-0.5 rounded font-bold border transition-all ${
                          isSel
                            ? 'bg-[#162839] text-white border-[#162839]'
                            : 'bg-white text-[#74777d] border-[#c4c6cd]'
                        }`}
                      >
                        {isSel ? `✓ ${name}` : `+ ${name}`}
                      </button>
                    );
                  })}
                </div>
              </div>

              {selectedCompareKeys.length === 2 && (
                <button
                  onClick={() => setIsCompareModalOpen(true)}
                  className="w-full bg-[#9a442a] text-white text-xs font-bold py-1.5 rounded-lg hover:opacity-90 transition-opacity shadow-xs flex items-center justify-center gap-1"
                >
                  <span className="material-symbols-outlined text-sm">auto_awesome</span>
                  查看【{selectedCompareKeys[0] === 'safe' ? '稳妥' : selectedCompareKeys[0] === 'fresh' ? '新鲜' : '突破'} vs {selectedCompareKeys[1] === 'safe' ? '稳妥' : selectedCompareKeys[1] === 'fresh' ? '新鲜' : '突破'}】 AI 对比分析
                </button>
              )}
            </div>
          )}
        </div>
      </header>

      <main className="max-w-md mx-auto">
        {/* Safe Category */}
        {(() => {
          const varIdx = variantsIdx.safe || 0;
          const currentSafe = liveLooks?.safe || EMPTY_LOOKS.safe;
          const ratingKey = `safe-${varIdx}`;
          const currentRating = ratings[ratingKey];

          return (
            <section className="py-12 px-6 flex flex-col items-center border-b border-[#e4e2dd]/50 relative">
              <div className="absolute top-4 inset-x-6 flex justify-between items-center z-20">
                <button
                  onClick={() => {
                    if (!isCompareMode) setIsCompareMode(true);
                    toggleCompareKey('safe');
                  }}
                  className={`text-[10px] font-bold px-2.5 py-1 rounded-full border transition-all flex items-center gap-1 shadow-2xs ${
                    selectedCompareKeys.includes('safe')
                      ? 'bg-[#162839] text-white border-[#162839]'
                      : 'bg-white/80 text-[#162839] border-[#162839]/30 hover:bg-[#162839] hover:text-white'
                  }`}
                >
                  <span className="material-symbols-outlined text-xs">
                    {selectedCompareKeys.includes('safe') ? 'check_box' : 'add_box'}
                  </span>
                  {selectedCompareKeys.includes('safe') ? '已选对比 (Look 01)' : '+ 加入对比'}
                </button>
                <button
                  onClick={(e) => toggleLike('safe', e)}
                  className="p-1.5 rounded-full hover:bg-black/5 transition-colors bg-white/60 border border-[#c4c6cd]/30"
                  title={liked['safe'] ? '取消收藏' : '收藏此 Look'}
                >
                  <span className={`material-symbols-outlined text-lg ${liked['safe'] ? 'text-[#9a442a]' : 'text-[#74777d]'}`}>
                    {liked['safe'] ? 'favorite' : 'favorite_border'}
                  </span>
                </button>
              </div>

              <div className="relative w-full mb-10 flex flex-col items-center">
                <div className="text-center z-10">
                  <h2 className="font-serif-display text-3xl text-[#162839] font-semibold">稳妥</h2>
                  <div className="mt-2 flex items-center justify-center gap-2">
                    <span className="bg-[#9a442a] text-white font-mono text-[10px] uppercase tracking-[0.2em] px-2.5 py-1 inline-block -rotate-2 shadow-sm font-semibold rounded-sm">
                      S A F E
                    </span>
                    <span className="bg-[#162839]/10 text-[#162839] text-[9px] font-mono px-2 py-0.5 rounded font-bold">
                      {currentSafe.tag}
                    </span>
                  </div>
                  <div className="flex items-center justify-center gap-2 mt-4">
                    <div className="w-4 h-px bg-[#c4c6cd]"></div>
                    <span className="text-[10px] uppercase tracking-wider text-[#74777d]">Editorial No. 01</span>
                    <div className="w-4 h-px bg-[#c4c6cd]"></div>
                  </div>
                </div>
              </div>

              <LookItems items={currentSafe.items} onSelect={(item) => setActiveModalItem({ title: item.name, desc: item.desc })} />

              <div className="mt-10 text-center max-w-[280px]">
                <p className="font-serif-display text-[14px] text-[#162839] font-medium leading-relaxed">
                  {currentSafe.description}
                </p>
                <p className="text-[11px] text-[#43474c] mt-2 border-t border-[#c4c6cd]/30 pt-2">
                  {currentSafe.reason || '先确认真实衣橱，再由 AI 根据 Style DNA 生成。'}
                </p>

                {/* AI Swap / 换一换 Button */}
                <div className="mt-3 flex justify-center">
                  <button
                    onClick={() => handleSwapLook('safe')}
                    disabled={swappingTier === 'safe'}
                    className="text-[11px] font-bold text-[#9a442a] bg-[#9a442a]/10 hover:bg-[#9a442a]/20 border border-[#9a442a]/30 px-4 py-1.5 rounded-full flex items-center justify-center gap-1.5 transition-all shadow-xs"
                  >
                    <span className={`material-symbols-outlined text-xs ${swappingTier === 'safe' ? 'animate-spin' : ''}`}>
                      autorenew
                    </span>
                    {swappingTier === 'safe' ? 'AI 智能计算新搭配中...' : 'AI 换一换'}
                  </button>
                </div>

                {/* Look Rating & AI Feedback trigger */}
                <div className="mt-3 pt-3 border-t border-[#c4c6cd]/30 w-full flex flex-col items-center">
                  <button
                    onClick={() => openRatingModal(ratingKey, `Look 01 / 稳妥 (${currentSafe.title})`, currentSafe.imageUrl)}
                    className="text-[11px] font-semibold tracking-wider text-[#162839] border border-[#162839]/40 hover:bg-[#162839] hover:text-white transition-all px-4 py-1.5 rounded-full flex items-center gap-1.5 shadow-xs bg-white/50"
                  >
                    <span className="material-symbols-outlined text-sm text-[#9a442a]">auto_awesome</span>
                    {currentRating ? `已反馈 (${currentRating.rating}★)` : '打分与反馈'}
                  </button>
                </div>
              </div>
            </section>
          );
        })()}

        {/* Fresh Category */}
        {(() => {
          const varIdx = variantsIdx.fresh || 0;
          const currentFresh = liveLooks?.fresh || EMPTY_LOOKS.fresh;
          const ratingKey = `fresh-${varIdx}`;
          const currentRating = ratings[ratingKey];

          return (
            <section className="py-12 px-6 flex flex-col items-center border-b border-[#e4e2dd]/50 relative">
              <div className="absolute top-4 inset-x-6 flex justify-between items-center z-20">
                <button
                  onClick={() => {
                    if (!isCompareMode) setIsCompareMode(true);
                    toggleCompareKey('fresh');
                  }}
                  className={`text-[10px] font-bold px-2.5 py-1 rounded-full border transition-all flex items-center gap-1 shadow-2xs ${
                    selectedCompareKeys.includes('fresh')
                      ? 'bg-[#162839] text-white border-[#162839]'
                      : 'bg-white/80 text-[#162839] border-[#162839]/30 hover:bg-[#162839] hover:text-white'
                  }`}
                >
                  <span className="material-symbols-outlined text-xs">
                    {selectedCompareKeys.includes('fresh') ? 'check_box' : 'add_box'}
                  </span>
                  {selectedCompareKeys.includes('fresh') ? '已选对比 (Look 02)' : '+ 加入对比'}
                </button>
                <button
                  onClick={(e) => toggleLike('fresh', e)}
                  className="p-1.5 rounded-full hover:bg-black/5 transition-colors bg-white/60 border border-[#c4c6cd]/30"
                  title={liked['fresh'] ? '取消收藏' : '收藏此 Look'}
                >
                  <span className={`material-symbols-outlined text-lg ${liked['fresh'] ? 'text-[#9a442a]' : 'text-[#74777d]'}`}>
                    {liked['fresh'] ? 'favorite' : 'favorite_border'}
                  </span>
                </button>
              </div>

              <div className="relative w-full mb-10 flex flex-col items-center">
                <div className="text-center z-10">
                  <h2 className="font-serif-display text-3xl text-[#162839] font-semibold">新鲜</h2>
                  <div className="mt-2 flex items-center justify-center gap-2">
                    <span className="bg-[#9a442a] text-white font-mono text-[10px] uppercase tracking-[0.2em] px-2.5 py-1 inline-block rotate-3 shadow-sm font-semibold rounded-sm">
                      F R E S H
                    </span>
                    <span className="bg-[#162839]/10 text-[#162839] text-[9px] font-mono px-2 py-0.5 rounded font-bold">
                      {currentFresh.tag}
                    </span>
                  </div>
                  <div className="flex items-center justify-center gap-2 mt-4">
                    <div className="w-4 h-px bg-[#c4c6cd]"></div>
                    <span className="text-[10px] uppercase tracking-wider text-[#74777d]">Editorial No. 02</span>
                    <div className="w-4 h-px bg-[#c4c6cd]"></div>
                  </div>
                </div>
              </div>

              <LookItems items={currentFresh.items} onSelect={(item) => setActiveModalItem({ title: item.name, desc: item.desc })} />

              <div className="mt-10 text-center max-w-[280px]">
                <p className="font-serif-display text-[14px] text-[#162839] font-medium leading-relaxed">
                  {currentFresh.description}
                </p>
                <p className="text-[11px] text-[#43474c] mt-2 border-t border-[#c4c6cd]/30 pt-2">
                  {currentFresh.reason || '先确认真实衣橱，再由 AI 根据 Style DNA 生成。'}
                </p>

                {/* AI Swap / 换一换 Button */}
                <div className="mt-3 flex justify-center">
                  <button
                    onClick={() => handleSwapLook('fresh')}
                    disabled={swappingTier === 'fresh'}
                    className="text-[11px] font-bold text-[#9a442a] bg-[#9a442a]/10 hover:bg-[#9a442a]/20 border border-[#9a442a]/30 px-4 py-1.5 rounded-full flex items-center justify-center gap-1.5 transition-all shadow-xs"
                  >
                    <span className={`material-symbols-outlined text-xs ${swappingTier === 'fresh' ? 'animate-spin' : ''}`}>
                      autorenew
                    </span>
                    {swappingTier === 'fresh' ? 'AI 智能计算新搭配中...' : 'AI 换一换'}
                  </button>
                </div>

                {/* Look Rating & AI Feedback trigger */}
                <div className="mt-3 pt-3 border-t border-[#c4c6cd]/30 w-full flex flex-col items-center">
                  <button
                    onClick={() => openRatingModal(ratingKey, `Look 02 / 新鲜 (${currentFresh.title})`, currentFresh.imageUrl)}
                    className="text-[11px] font-semibold tracking-wider text-[#162839] border border-[#162839]/40 hover:bg-[#162839] hover:text-white transition-all px-4 py-1.5 rounded-full flex items-center gap-1.5 shadow-xs bg-white/50"
                  >
                    <span className="material-symbols-outlined text-sm text-[#9a442a]">auto_awesome</span>
                    {currentRating ? `已反馈 (${currentRating.rating}★)` : '打分与反馈'}
                  </button>
                </div>
              </div>
            </section>
          );
        })()}

        {/* Stretch Category */}
        {(() => {
          const varIdx = variantsIdx.stretch || 0;
          const currentStretch = liveLooks?.stretch || EMPTY_LOOKS.stretch;
          const ratingKey = `stretch-${varIdx}`;
          const currentRating = ratings[ratingKey];

          return (
            <section className="py-12 px-6 flex flex-col items-center relative">
              <div className="absolute top-4 inset-x-6 flex justify-between items-center z-20">
                <button
                  onClick={() => {
                    if (!isCompareMode) setIsCompareMode(true);
                    toggleCompareKey('stretch');
                  }}
                  className={`text-[10px] font-bold px-2.5 py-1 rounded-full border transition-all flex items-center gap-1 shadow-2xs ${
                    selectedCompareKeys.includes('stretch')
                      ? 'bg-[#162839] text-white border-[#162839]'
                      : 'bg-white/80 text-[#162839] border-[#162839]/30 hover:bg-[#162839] hover:text-white'
                  }`}
                >
                  <span className="material-symbols-outlined text-xs">
                    {selectedCompareKeys.includes('stretch') ? 'check_box' : 'add_box'}
                  </span>
                  {selectedCompareKeys.includes('stretch') ? '已选对比 (Look 03)' : '+ 加入对比'}
                </button>
                <button
                  onClick={(e) => toggleLike('stretch', e)}
                  className="p-1.5 rounded-full hover:bg-black/5 transition-colors bg-white/60 border border-[#c4c6cd]/30"
                  title={liked['stretch'] ? '取消收藏' : '收藏此 Look'}
                >
                  <span className={`material-symbols-outlined text-lg ${liked['stretch'] ? 'text-[#9a442a]' : 'text-[#74777d]'}`}>
                    {liked['stretch'] ? 'favorite' : 'favorite_border'}
                  </span>
                </button>
              </div>

              <div className="relative w-full mb-10 flex flex-col items-center">
                <div className="text-center z-10">
                  <h2 className="font-serif-display text-3xl text-[#162839] font-semibold">突破</h2>
                  <div className="mt-2 flex items-center justify-center gap-2">
                    <span className="bg-[#9a442a] text-white font-mono text-[10px] uppercase tracking-[0.2em] px-2.5 py-1 inline-block -rotate-1 shadow-sm font-semibold rounded-sm">
                      S T R E T C H
                    </span>
                    <span className="bg-[#162839]/10 text-[#162839] text-[9px] font-mono px-2 py-0.5 rounded font-bold">
                      {currentStretch.tag}
                    </span>
                  </div>
                  <div className="flex items-center justify-center gap-2 mt-4">
                    <div className="w-4 h-px bg-[#c4c6cd]"></div>
                    <span className="text-[10px] uppercase tracking-wider text-[#74777d]">Editorial No. 03</span>
                    <div className="w-4 h-px bg-[#c4c6cd]"></div>
                  </div>
                </div>
              </div>

              <LookItems items={currentStretch.items} onSelect={(item) => setActiveModalItem({ title: item.name, desc: item.desc })} />

              <div className="mt-10 text-center max-w-[280px]">
                <p className="font-serif-display text-[14px] text-[#162839] font-medium leading-relaxed">
                  {currentStretch.description}
                </p>
                <p className="text-[11px] text-[#43474c] mt-2 border-t border-[#c4c6cd]/30 pt-2">
                  {currentStretch.reason || '先确认真实衣橱，再由 AI 根据 Style DNA 生成。'}
                </p>

                {/* AI Swap / 换一换 Button */}
                <div className="mt-3 flex justify-center">
                  <button
                    onClick={() => handleSwapLook('stretch')}
                    disabled={swappingTier === 'stretch'}
                    className="text-[11px] font-bold text-[#9a442a] bg-[#9a442a]/10 hover:bg-[#9a442a]/20 border border-[#9a442a]/30 px-4 py-1.5 rounded-full flex items-center justify-center gap-1.5 transition-all shadow-xs"
                  >
                    <span className={`material-symbols-outlined text-xs ${swappingTier === 'stretch' ? 'animate-spin' : ''}`}>
                      autorenew
                    </span>
                    {swappingTier === 'stretch' ? 'AI 智能计算新搭配中...' : 'AI 换一换'}
                  </button>
                </div>

                {/* Look Rating & AI Feedback trigger */}
                <div className="mt-3 pt-3 border-t border-[#c4c6cd]/30 w-full flex flex-col items-center">
                  <button
                    onClick={() => openRatingModal(ratingKey, `Look 03 / 突破 (${currentStretch.title})`, currentStretch.imageUrl)}
                    className="text-[11px] font-semibold tracking-wider text-[#162839] border border-[#162839]/40 hover:bg-[#162839] hover:text-white transition-all px-4 py-1.5 rounded-full flex items-center gap-1.5 shadow-xs bg-white/50"
                  >
                    <span className="material-symbols-outlined text-sm text-[#9a442a]">auto_awesome</span>
                    {currentRating ? `已反馈 (${currentRating.rating}★)` : '打分与反馈'}
                  </button>
                </div>
              </div>
            </section>
          );
        })()}
      </main>

      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed top-20 left-1/2 -translate-x-1/2 z-50 bg-[#162839] text-white px-5 py-3 rounded-lg shadow-2xl text-xs font-medium border border-[#9a442a]/50 animate-fade-in flex items-center gap-2 max-w-xs text-center">
          <span className="material-symbols-outlined text-[#f4dfcb] text-base">auto_awesome</span>
          {toastMessage}
        </div>
      )}

      {/* Item Detail Modal */}
      {activeModalItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="bg-[#fbf9f4] p-6 max-w-sm w-full rounded-lg border border-[#162839] shadow-2xl relative">
            <h3 className="font-serif-display text-lg text-[#162839] font-bold mb-2">{activeModalItem.title}</h3>
            <p className="text-sm text-[#43474c] mb-6 leading-relaxed">{activeModalItem.desc}</p>
            <button
              onClick={() => setActiveModalItem(null)}
              className="w-full bg-[#162839] text-white py-2 rounded text-xs font-semibold uppercase tracking-widest hover:opacity-90 transition-opacity"
            >
              关闭详情
            </button>
          </div>
        </div>
      )}

      {/* Look Rating & AI Learning Modal */}
      {activeRatingModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 animate-fade-in">
          <div className="bg-[#fbf9f4] p-6 max-w-sm w-full rounded-lg border border-[#162839] shadow-2xl relative">
            <div className="flex justify-between items-center mb-3">
              <span className="text-[10px] bg-[#9a442a] text-white px-2 py-0.5 rounded font-mono font-semibold uppercase tracking-widest">
                AI Taste Learning
              </span>
              <button
                onClick={() => setActiveRatingModal(null)}
                className="text-[#74777d] hover:text-[#162839]"
              >
                <span className="material-symbols-outlined text-lg">close</span>
              </button>
            </div>

            <h3 className="font-serif-display text-lg text-[#162839] font-bold mb-1">
              评价 {activeRatingModal.title}
            </h3>
            <p className="text-[11px] text-[#43474c] mb-4">
              你的每次打分与反馈，都会实时反哺并演进 AI 审美模型
            </p>

            {/* 5-Star Selection */}
            <div className="mb-4 text-center bg-[#f5f3ee] p-3 rounded border border-[#c4c6cd]/30">
              <label className="block text-[11px] text-[#43474c] font-semibold mb-1">选择评分 (1 - 5 星)</label>
              <div className="flex justify-center gap-2 text-2xl cursor-pointer">
                {[1, 2, 3, 4, 5].map((star) => (
                  <button
                    key={star}
                    type="button"
                    onClick={() => setCurrentStars(star)}
                    className="hover:scale-125 transition-transform"
                  >
                    <span className={star <= currentStars ? 'text-[#9a442a]' : 'text-[#c4c6cd]'}>
                      ★
                    </span>
                  </button>
                ))}
              </div>
            </div>

            {/* Feedback Quick Tags */}
            <div className="mb-4">
              <label className="block text-[11px] text-[#43474c] font-semibold mb-1.5">快速审美反馈标签</label>
              <div className="flex flex-wrap gap-1.5">
                {FEEDBACK_TAG_OPTIONS.map((tag) => {
                  const isSelected = selectedTags.includes(tag);
                  return (
                    <button
                      key={tag}
                      type="button"
                      onClick={() => handleTagToggle(tag)}
                      className={`text-[11px] px-2.5 py-1 rounded transition-colors border ${
                        isSelected
                          ? 'bg-[#162839] text-white border-[#162839]'
                          : 'bg-white text-[#43474c] border-[#c4c6cd] hover:border-[#162839]'
                      }`}
                    >
                      {tag}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Text Comment */}
            <div className="mb-5">
              <label className="block text-[11px] text-[#43474c] font-semibold mb-1">具体修改建议 (可选)</label>
              <textarea
                value={commentText}
                onChange={(e) => setCommentText(e.target.value)}
                placeholder="例如: 配色不错，但希望整体氛围再休闲一些，多看些轻质感衬衫..."
                className="w-full p-2 text-xs border border-[#c4c6cd] rounded bg-white text-[#162839] focus:outline-none focus:border-[#162839] h-20 resize-none"
              />
            </div>

            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setActiveRatingModal(null)}
                className="flex-1 border border-[#162839] text-[#162839] py-2 rounded text-xs font-semibold uppercase tracking-wider"
              >
                取消
              </button>
              <button
                type="button"
                onClick={submitRating}
                className="flex-1 bg-[#162839] text-white py-2 rounded text-xs font-semibold uppercase tracking-wider hover:opacity-90 transition-opacity flex items-center justify-center gap-1"
              >
                <span className="material-symbols-outlined text-sm">auto_awesome</span>
                提交反馈
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Look PK Comparison Modal */}
      {isCompareModalOpen && selectedCompareKeys.length === 2 && (() => {
        const keyA = selectedCompareKeys[0];
        const keyB = selectedCompareKeys[1];
        const analysis = getAIComparisonAnalysis(keyA, keyB);
        const lookA = analysis.lookA;
        const lookB = analysis.lookB;

        return (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-3 animate-fade-in overflow-y-auto">
            <div className="bg-[#fbf9f4] p-4 sm:p-5 max-w-md w-full rounded-2xl border border-[#162839] shadow-2xl relative my-auto max-h-[92vh] flex flex-col">
              {/* Modal Header */}
              <div className="flex justify-between items-center pb-3 border-b border-[#c4c6cd]/40 shrink-0">
                <div className="flex items-center gap-2">
                  <span className="bg-[#9a442a] text-white font-mono text-[9px] uppercase px-2 py-0.5 rounded font-bold tracking-wider">
                    AI Look PK
                  </span>
                  <h3 className="text-xs font-bold text-[#162839]">Look 方案对比与 AI 风格差异</h3>
                </div>
                <button
                  onClick={() => setIsCompareModalOpen(false)}
                  className="text-[#74777d] hover:text-[#162839] p-1 rounded-full hover:bg-black/5"
                >
                  <span className="material-symbols-outlined text-lg">close</span>
                </button>
              </div>

              {/* Modal Body - Scrollable */}
              <div className="overflow-y-auto my-3 space-y-3.5 pr-1 flex-1">
                {/* Side by Side Look Comparison Cards */}
                <div className="grid grid-cols-2 gap-2.5">
                  {/* Look A Card */}
                  <div className="bg-white p-2.5 rounded-xl border border-[#c4c6cd]/50 shadow-2xs flex flex-col justify-between">
                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <span className="bg-[#162839]/10 text-[#162839] text-[9px] font-bold px-1.5 py-0.5 rounded font-mono">
                          {lookA.tierName}
                        </span>
                        <span className="text-[9px] text-[#9a442a] font-bold">{lookA.tag}</span>
                      </div>
                      <div className="aspect-3/4 rounded-lg overflow-hidden border border-[#c4c6cd]/30 bg-[#f8f6f0] my-1.5 relative">
                        <img src={lookA.imageUrl} alt={lookA.title} className="w-full h-full object-cover" />
                      </div>
                      <p className="text-[10px] text-[#162839] font-bold leading-tight line-clamp-2 min-h-[26px]">
                        {lookA.description}
                      </p>
                    </div>

                    {/* Items Breakdown */}
                    <div className="mt-2 pt-2 border-t border-[#e4e2dd]/60 space-y-1">
                      <span className="text-[9px] text-[#74777d] font-bold block">单品构成:</span>
                      <div className="grid grid-cols-3 gap-1">
                        {lookA.items.map((item, i) => (
                          <div key={i} className="flex flex-col items-center text-center">
                            <img src={item.img} alt={item.name} className="w-full aspect-square object-cover rounded border border-[#c4c6cd]/30 bg-[#f8f6f0]" />
                            <span className="text-[8px] text-[#43474c] truncate w-full mt-0.5">{item.name}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Look B Card */}
                  <div className="bg-white p-2.5 rounded-xl border border-[#c4c6cd]/50 shadow-2xs flex flex-col justify-between">
                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <span className="bg-[#162839]/10 text-[#162839] text-[9px] font-bold px-1.5 py-0.5 rounded font-mono">
                          {lookB.tierName}
                        </span>
                        <span className="text-[9px] text-[#9a442a] font-bold">{lookB.tag}</span>
                      </div>
                      <div className="aspect-3/4 rounded-lg overflow-hidden border border-[#c4c6cd]/30 bg-[#f8f6f0] my-1.5 relative">
                        <img src={lookB.imageUrl} alt={lookB.title} className="w-full h-full object-cover" />
                      </div>
                      <p className="text-[10px] text-[#162839] font-bold leading-tight line-clamp-2 min-h-[26px]">
                        {lookB.description}
                      </p>
                    </div>

                    {/* Items Breakdown */}
                    <div className="mt-2 pt-2 border-t border-[#e4e2dd]/60 space-y-1">
                      <span className="text-[9px] text-[#74777d] font-bold block">单品构成:</span>
                      <div className="grid grid-cols-3 gap-1">
                        {lookB.items.map((item, i) => (
                          <div key={i} className="flex flex-col items-center text-center">
                            <img src={item.img} alt={item.name} className="w-full aspect-square object-cover rounded border border-[#c4c6cd]/30 bg-[#f8f6f0]" />
                            <span className="text-[8px] text-[#43474c] truncate w-full mt-0.5">{item.name}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>

                {/* AI Analysis Box */}
                <div className="bg-[#f5f3ee] p-3.5 rounded-xl border border-[#162839]/20 space-y-3">
                  <div className="flex items-center gap-1.5 pb-2 border-b border-[#c4c6cd]/40">
                    <span className="material-symbols-outlined text-base text-[#9a442a]">auto_awesome</span>
                    <h4 className="text-xs font-bold text-[#162839]">AI 建议的分析对比框</h4>
                  </div>

                  {/* Summary sentence */}
                  <p className="text-[11px] text-[#162839] font-medium leading-relaxed bg-white p-2.5 rounded-lg border border-[#c4c6cd]/30 shadow-2xs">
                    {analysis.summary}
                  </p>

                  {/* Dimension Comparison Score Bars */}
                  <div className="space-y-2 bg-white p-2.5 rounded-lg border border-[#c4c6cd]/30 text-[10px]">
                    <div>
                      <div className="flex justify-between text-[#43474c] font-bold mb-1">
                        <span>👔 正式度与干练指数 (Formality)</span>
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <div className="flex justify-between text-[9px] text-[#162839] mb-0.5 font-medium">
                            <span>{lookA.tierName.split(' ')[0]}</span>
                            <span>{analysis.formalityA}%</span>
                          </div>
                          <div className="w-full bg-[#e4e2dd] h-1.5 rounded-full overflow-hidden">
                            <div className="bg-[#162839] h-full" style={{ width: `${analysis.formalityA}%` }}></div>
                          </div>
                        </div>
                        <div>
                          <div className="flex justify-between text-[9px] text-[#162839] mb-0.5 font-medium">
                            <span>{lookB.tierName.split(' ')[0]}</span>
                            <span>{analysis.formalityB}%</span>
                          </div>
                          <div className="w-full bg-[#e4e2dd] h-1.5 rounded-full overflow-hidden">
                            <div className="bg-[#9a442a] h-full" style={{ width: `${analysis.formalityB}%` }}></div>
                          </div>
                        </div>
                      </div>
                    </div>

                    <div>
                      <div className="flex justify-between text-[#43474c] font-bold mb-1">
                        <span>☕ 视觉松弛感与亲和度 (Relaxation)</span>
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <div className="flex justify-between text-[9px] text-[#162839] mb-0.5 font-medium">
                            <span>{lookA.tierName.split(' ')[0]}</span>
                            <span>{analysis.relaxA}%</span>
                          </div>
                          <div className="w-full bg-[#e4e2dd] h-1.5 rounded-full overflow-hidden">
                            <div className="bg-[#162839] h-full" style={{ width: `${analysis.relaxA}%` }}></div>
                          </div>
                        </div>
                        <div>
                          <div className="flex justify-between text-[9px] text-[#162839] mb-0.5 font-medium">
                            <span>{lookB.tierName.split(' ')[0]}</span>
                            <span>{analysis.relaxB}%</span>
                          </div>
                          <div className="w-full bg-[#e4e2dd] h-1.5 rounded-full overflow-hidden">
                            <div className="bg-[#9a442a] h-full" style={{ width: `${analysis.relaxB}%` }}></div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Highlights Breakdown */}
                  <div className="space-y-1.5 text-[10px]">
                    <div className="bg-white p-2 rounded-lg border border-[#c4c6cd]/30">
                      <span className="font-bold text-[#162839] block mb-0.5">✦ 核心材质与轮廓差异:</span>
                      <p className="text-[10px] text-[#162839]">{analysis.highlightA}</p>
                      <p className="text-[10px] text-[#9a442a] mt-1">{analysis.highlightB}</p>
                    </div>

                    <div className="bg-[#9a442a]/10 p-2 rounded-lg border border-[#9a442a]/20 text-[#162839]">
                      <span className="font-bold text-[#9a442a] block mb-0.5">💡 AI 穿搭场景建议:</span>
                      <p className="text-[10px] text-[#162839] leading-normal">{analysis.occasionAdvice}</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Modal Footer */}
              <div className="pt-2 border-t border-[#c4c6cd]/40 flex gap-2 shrink-0">
                <button
                  onClick={() => setIsCompareModalOpen(false)}
                  className="flex-1 border border-[#162839] text-[#162839] py-2 rounded-lg text-xs font-bold hover:bg-[#162839]/5 transition-colors"
                >
                  调整选方案
                </button>
                <button
                  onClick={() => {
                    setIsCompareModalOpen(false);
                    triggerToast(`✨ 已选定【${lookA.tierName.split(' ')[0]} vs ${lookB.tierName.split(' ')[0]}】对比方案！`);
                  }}
                  className="flex-1 bg-[#162839] text-white py-2 rounded-lg text-xs font-bold hover:opacity-90 transition-opacity shadow-xs flex items-center justify-center gap-1"
                >
                  <span className="material-symbols-outlined text-sm">check_circle</span>
                  采纳推荐
                </button>
              </div>
            </div>
          </div>
        );
      })()}

      {/* Unified Bottom Navigation Bar */}
      <BottomNav currentScreen="today" onNavigate={onNavigate} />
    </div>
  );
};
