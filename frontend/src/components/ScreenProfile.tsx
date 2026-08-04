import React, { useState, useEffect } from 'react';
import { ScreenId, LookRating, FavoriteLook, HistoryLook } from '../types';
import { api, confirmFeedback, mapHistoryLook, paletteHex, visibleStyleTags } from '../lib/api.mjs';
import { BottomNav } from './BottomNav';
import { SideDrawer } from './SideDrawer';

interface ScreenProfileProps {
  onNavigate: (screen: ScreenId) => void;
}

const IMAGE_FALLBACKS: Record<string, string> = {
  safe: 'https://lh3.googleusercontent.com/aida-public/AB6AXuDFEJapTzg7M2pWwwrAPXMMImbFzrYpkWckOASqNeyP-hx0RuVCZMR_hOAczTSsxi88EKn-yAhj3v12qBClhH3X2JUBtmX-3No4Q3tHG7M_qgxJU3BpZ9Z7ux-iGduVDAShKM_VfHmG1WLA5irrPRU_a5ZMddYMH0sZvcH_Y93s-JrfJ-IU6IenJUxj29G4AEK2wyyihIgAnNwgsCmoYkHhoyU3q7kvlRPI7CA1as9nTSGeCo8728tJ',
  fresh: 'https://lh3.googleusercontent.com/aida-public/AB6AXuCHxxA9TF55gxJT7Guqb18Wfu94ote5YoOVoiOJhoRQYcplRQBhb7aUmcHkl5_sbSbZvBGRN5Hmlnk6N7L7A58H7jb5ASvriWyvc9Gp9efDZ8M05YMdF2GQ079oj50pyhGPIRg_EJrSbJJhs3EWLJOz9lfvlXZbQMe2f0ZPiXX_vN5aKJ7OIx97fZSLYjGUTMPxPoGvl7eDUBAEVv_-nGfiOMENaf_v-D13cDyTxvI3ifa8oe0SxF8F',
  stretch: 'https://lh3.googleusercontent.com/aida-public/AB6AXuB9zc4UnQuZ3eYOMp1SlgcMTx5GDWw5FJK10oRRxpGWCuwq3FiKm2waRVfrM-0uant5SbFTO2YG7DRog2z_J7sR2yWBKiMZftRXOfEeG_8PKjtVe6sP_Mbupoui5qF0lLguKCsQVKAgR-UiqSTBbMFTVB3loUSKfVC_SAoH_eTx4AeOm7Yn7u-KLIfadj16dH8E9rkPP2uXl60Hc51AOCUSyNN2SENNUrp_E0-1_Hk7a4fYzg4cWR1H'
};

const DEFAULT_RATINGS: Record<string, LookRating> = {
  'safe-0': {
    lookId: 'safe-0',
    lookTitle: 'Look 01 / 稳妥 (日杂经典)',
    rating: 5,
    tags: ['🎨 色彩搭配好', '✂️ 廓形很满意'],
    comment: '精纺衬衫搭配藏青西裤非常干净利落，符合通勤预期！',
    timestamp: '07-30 09:15',
    aiAdjustment: '已将【深海蓝与白衬衫】沉淀至核心品味 DNA',
    lookImage: IMAGE_FALLBACKS.safe
  },
  'fresh-0': {
    lookId: 'fresh-0',
    lookTitle: 'Look 02 / 新鲜 (松弛休假)',
    rating: 4,
    tags: ['👔 过于正式', '👟 鞋子不太搭'],
    comment: '衬衫希望能更有松弛感，鞋子想换成小白鞋。',
    timestamp: '07-29 14:30',
    aiAdjustment: '已调高【松弛休假风】权重 +15%，减少工整正装推荐',
    lookImage: IMAGE_FALLBACKS.fresh
  },
  'stretch-0': {
    lookId: 'stretch-0',
    lookTitle: 'Look 03 / 突破 (工装廓形)',
    rating: 5,
    tags: ['🧵 面料很高级', '轻熟干练'],
    comment: '橄榄绿无结构西装很有个性，试着穿去参加设计展！',
    timestamp: '07-28 18:20',
    aiAdjustment: '已新增【无结构廓形外套】推荐算法规则',
    lookImage: IMAGE_FALLBACKS.stretch
  }
};

const RATING_TAG_OPTIONS = ['🎨 色彩搭配好', '👔 过于正式', '👟 鞋子不太搭', '✂️ 廓形很满意', '🧵 面料很高级', '轻熟干练', '缺乏特色'];

const getLookImageUrl = (item: LookRating) => {
  if (item.lookImage) return item.lookImage;
  const key = item.lookId.split('-')[0];
  return IMAGE_FALLBACKS[key] || IMAGE_FALLBACKS.safe;
};

const EMPTY_TAG_PREFERENCES = { pinned: [], hidden: [], aliases: {} };

const uniqueTags = (tags: string[]) => [...new Set(tags.filter(Boolean))];

const TotalLookThumbnails = ({ items, fallback, alt }: { items?: { name: string; img: string }[]; fallback: string; alt: string }) => (
  items?.length ? (
    <div className="grid w-14 shrink-0 grid-cols-3 gap-0.5 rounded-md border border-[#c4c6cd]/30 bg-[#f5f3ee] p-0.5">
      {items.map((item, index) => <img key={`${item.name}-${index}`} src={item.img} alt={item.name} className="aspect-square w-full rounded-sm object-cover" />)}
    </div>
  ) : <img src={fallback} alt={alt} className="w-14 h-18 object-cover rounded-md border border-[#c4c6cd]/30 bg-[#f5f3ee] shrink-0" />
);

export const ScreenProfile: React.FC<ScreenProfileProps> = ({ onNavigate }) => {
  const [styleId, setStyleId] = useState('894-FX-21');
  const [isEditing, setIsEditing] = useState(false);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [profile, setProfile] = useState<any>(null);
  const [modalType, setModalType] = useState<'history' | 'favorites' | 'ratings' | 'settings' | null>(null);
  const [isManagingTags, setIsManagingTags] = useState(false);
  const [isMergingTags, setIsMergingTags] = useState(false);
  const [mergeTags, setMergeTags] = useState<string[]>([]);
  const [mergeName, setMergeName] = useState('');
  const [tagError, setTagError] = useState('');

  // Ratings, Favorites, and History
  const [ratings, setRatings] = useState<Record<string, LookRating>>({});
  const [favoritesList, setFavoritesList] = useState<FavoriteLook[]>([]);
  const [historyList, setHistoryList] = useState<HistoryLook[]>([]);

  // Editing rating item state
  const [editingRating, setEditingRating] = useState<LookRating | null>(null);

  const loadData = async () => {
    try {
      const savedRatings = localStorage.getItem('OUTFIT_AI_LOOK_RATINGS');
      if (savedRatings) {
        setRatings(JSON.parse(savedRatings));
      } else {
        setRatings({});
      }
      const [loadedProfile, wardrobe, archive, recent] = await Promise.all([
        api.profile(),
        api.wardrobe(),
        api.history({ scope: 'archive' }),
        api.history({ scope: 'recent' }),
      ]);
      setProfile(loadedProfile);
      const byId = new Map(wardrobe.map((item: any) => [item.id, item]));
      const mappedHistory: HistoryLook[] = [...archive, ...recent].map((row: any) => mapHistoryLook(row, byId));
      setHistoryList(mappedHistory);
      const serverRatings = Object.fromEntries(mappedHistory.filter((item) => item.rating).map((item) => [item.id, {
        lookId: item.id,
        historyId: item.historyId,
        lookTitle: item.title,
        rating: item.rating!,
        tags: [],
        timestamp: item.date,
        aiAdjustment: '已同步到 AI 品味备忘录',
        lookImage: item.imageUrl,
        lookItems: item.lookItems,
      }]));
      if (Object.keys(serverRatings).length) setRatings(serverRatings);
      setFavoritesList(mappedHistory.filter((item: any) => item.action === 'saved').map((item) => ({
        id: item.id,
        historyId: item.historyId,
        title: item.title,
        tag: item.tag,
        imageUrl: item.imageUrl,
        dateAdded: item.date,
        type: 'look' as const,
        description: item.description,
        lookItems: item.items,
        rating: item.rating,
        woreIt: item.woreIt,
        scope: item.scope,
      })));
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    void loadData();
    const handleStorageChange = () => void loadData();
    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, []);

  const saveUpdatedRating = async (updated: LookRating) => {
    if (updated.historyId) {
      try {
        await confirmFeedback(api.feedback, {
          history_id: updated.historyId,
          items_worn: historyList.find((item) => item.historyId === updated.historyId)?.itemIds || [],
          rating: updated.rating,
          sentiment: updated.comment,
          compliments: updated.tags,
        }, () => { setEditingRating(null); void loadData(); }, (error: unknown) => {
          setTagError(error instanceof Error ? error.message : '评分保存失败，请重试');
        });
      } catch {
        return;
      }
      return;
    }
    const newRatings = { ...ratings, [updated.lookId]: updated };
    setRatings(newRatings);
    try {
      localStorage.setItem('OUTFIT_AI_LOOK_RATINGS', JSON.stringify(newRatings));
      window.dispatchEvent(new Event('storage'));
    } catch (e) {
      console.error(e);
    }
    setEditingRating(null);
  };

  const deleteRating = (lookId: string) => {
    const newRatings = { ...ratings };
    delete newRatings[lookId];
    setRatings(newRatings);
    try {
      localStorage.setItem('OUTFIT_AI_LOOK_RATINGS', JSON.stringify(newRatings));
      window.dispatchEvent(new Event('storage'));
    } catch (e) {
      console.error(e);
    }
    setEditingRating(null);
  };

  const removeFavorite = async (id: string) => {
    const history = historyList.find((item) => item.id === id);
    if (history?.historyId) {
      try {
        await confirmFeedback(api.feedback, {
          history_id: history.historyId,
          items_worn: history.itemIds || [],
          action: 'shown',
        }, () => void loadData(), (error: unknown) => {
          setTagError(error instanceof Error ? error.message : '收藏状态同步失败');
        });
      } catch {
        return;
      }
      return;
    }
    const updated = favoritesList.filter((f) => f.id !== id);
    setFavoritesList(updated);
    try {
      localStorage.setItem('OUTFIT_AI_FAVORITES', JSON.stringify(updated));
      window.dispatchEvent(new Event('storage'));
    } catch (e) {
      console.error(e);
    }
  };

  const updateHistoryAction = async (history: HistoryLook, action?: 'shown' | 'saved' | 'worn', rating?: number) => {
    if (!history.historyId) return;
    try {
      await confirmFeedback(api.feedback, {
        history_id: history.historyId,
        items_worn: history.itemIds || [],
        ...(action ? { action } : {}),
        ...(rating ? { rating } : {}),
      }, () => void loadData(), (error: unknown) => {
        setTagError(error instanceof Error ? error.message : '操作同步失败');
      });
    } catch {
      // The displayed server-confirmed state remains unchanged.
    }
  };

  const ratingList: LookRating[] = Object.values(ratings);
  const ratingCount = ratingList.length;
  const tagPreferences = profile?.style_tag_preferences || EMPTY_TAG_PREFERENCES;
  const normalizeTag = (tag: string) => tagPreferences.aliases?.[tag] || tag;
  const coreTags = visibleStyleTags(profile?.style_keywords || [], tagPreferences, 7);
  const recentSignals = visibleStyleTags(profile?.recent_style_signals || [], tagPreferences, 3);
  const allTags = uniqueTags([...(profile?.style_keywords || []), ...(profile?.recent_style_signals || [])]);

  const saveTagProfile = async (nextProfile: any) => {
    const previousProfile = profile;
    setProfile(nextProfile);
    try {
      setProfile(await api.saveProfile(nextProfile));
      setTagError('');
    } catch (error) {
      setProfile(previousProfile);
      setTagError(error instanceof Error ? `保存失败：${error.message}` : '保存失败，请重试');
    }
  };

  const updateTagPreferences = (nextPreferences: any) => {
    if (!profile) return;
    void saveTagProfile({ ...profile, style_tag_preferences: nextPreferences });
  };

  const togglePinnedTag = (tag: string) => {
    const pinned = tagPreferences.pinned || [];
    if (pinned.includes(tag)) {
      updateTagPreferences({ ...tagPreferences, pinned: pinned.filter((value: string) => value !== tag) });
      return;
    }
    if (pinned.length >= 3) {
      setTagError('最多可置顶 3 个标签');
      return;
    }
    updateTagPreferences({ ...tagPreferences, pinned: [...pinned, tag] });
  };

  const toggleHiddenTag = (tag: string) => {
    const hidden = tagPreferences.hidden || [];
    const isHidden = hidden.includes(tag);
    updateTagPreferences({
      ...tagPreferences,
      hidden: isHidden ? hidden.filter((value: string) => value !== tag) : [...hidden, tag],
    });
  };

  const toggleMergeTag = (tag: string) => {
    setMergeTags((selected) => selected.includes(tag)
      ? selected.filter((value) => value !== tag)
      : selected.length < 2 ? [...selected, tag] : selected);
  };

  const confirmMerge = () => {
    const canonicalName = mergeName.trim();
    if (mergeTags.length !== 2 || !canonicalName) {
      setTagError('请选择恰好两个标签，并填写统一名称');
      return;
    }
    updateTagPreferences({
      ...tagPreferences,
      aliases: { ...tagPreferences.aliases, ...Object.fromEntries(mergeTags.map((tag) => [tag, canonicalName])) },
      hidden: (tagPreferences.hidden || []).filter((tag: string) => !mergeTags.includes(tag)),
    });
    setMergeTags([]);
    setMergeName('');
    setIsMergingTags(false);
  };

  return (
    <div className="bg-[#fbf9f4] text-[#1b1c19] min-h-screen pb-28 pt-16">
      {/* Side Drawer Menu */}
      <SideDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        currentScreen="profile"
        onNavigate={onNavigate}
      />

      {/* Mobile Header */}
      <header className="fixed top-0 inset-x-0 z-50 bg-[#fbf9f4]/95 backdrop-blur-sm flex justify-between items-center px-4 h-14 border-b border-[#e4e2dd]/60 max-w-md mx-auto">
        <button
          onClick={() => setIsDrawerOpen(true)}
          className="text-[#162839] hover:opacity-70 p-1.5 rounded transition-opacity"
          title="打开侧边导航"
        >
          <span className="material-symbols-outlined text-xl">menu</span>
        </button>
        <h1 className="text-xs font-bold text-[#162839] tracking-wider uppercase">
          Outfit-AI · 我的个人基因
        </h1>
        <button className="text-[#162839] hover:opacity-70 p-1.5 transition-opacity">
          <span className="material-symbols-outlined text-xl">shopping_bag</span>
        </button>
      </header>

      {/* Main Container tailored for Mobile Width */}
      <main className="max-w-md mx-auto px-4 pt-2 space-y-4">
        {/* User Identity Header Card */}
        <section className="bg-white p-3.5 rounded-xl border border-[#c4c6cd]/40 shadow-2xs">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-13 h-13 rounded-full overflow-hidden border border-[#c4c6cd]/50 bg-[#f5f3ee] shrink-0">
                <img
                  className="w-full h-full object-cover grayscale"
                  src="https://lh3.googleusercontent.com/aida-public/AB6AXuB346Shl7Tx7QMi79-y77wnqOc3s2h8f0fyXbI-MbYn7-naeC7q12d1VsABwlZ2J3wGGseeTPRd-shkz-RUigtvEQHlp6GbTBFtb8vGEDmhPrxJhJEH23duJvYQE7CSJMqCZxEFzPnLPU_hxCRk9lAcqv6FwnqCMqMg-qybj1EutWHO6fqU3l-t1JC-HfRS_vELz4I0eAb1cikEHBxyJfTqoXrYikLeLCscWnUxlsEVoin5xjXnxXOD"
                  alt="Curator Avatar"
                />
              </div>
              <div>
                <div className="flex items-center gap-1.5">
                  <h2 className="text-xs font-bold text-[#162839]">Style ID: {styleId}</h2>
                  <span className="bg-[#162839]/10 text-[#162839] text-[9px] font-mono px-1.5 py-0.2 rounded font-bold">
                    PRO
                  </span>
                </div>
                <p className="text-[11px] text-[#74777d] mt-0.5">穿搭基因库持续学习中</p>
              </div>
            </div>

            <div className="flex flex-col gap-1.5">
              <button
                onClick={() => setIsEditing(true)}
                className="bg-[#162839] text-white text-[10px] font-bold px-2.5 py-1.5 rounded-lg hover:opacity-90 transition-opacity"
              >
                编辑 ID
              </button>
              <button
                onClick={() => setModalType('settings')}
                className="border border-[#162839]/30 text-[#162839] text-[10px] font-semibold px-2.5 py-1 rounded-lg hover:bg-[#f5f3ee] transition-colors"
              >
                设置
              </button>
            </div>
          </div>
        </section>

        {/* Style DNA & Color Palette */}
        <section className="bg-white p-3.5 rounded-xl border border-[#c4c6cd]/40 shadow-2xs space-y-3">
          <div className="flex justify-between items-center pb-2 border-b border-[#e4e2dd]/60">
            <span className="text-xs font-bold text-[#162839] flex items-center gap-1.5">
              <span className="material-symbols-outlined text-sm text-[#9a442a]">palette</span>
              核心穿搭色板 (Style DNA)
            </span>
            <span className="text-[10px] text-[#74777d] font-mono">日杂高级微调</span>
          </div>

          <div className="grid grid-cols-3 gap-2 text-center">
            {[0, 1, 2].map((index) => {
              const name = profile?.palette?.[index] || '等待沉淀';
              const color = paletteHex(name);
              return (
                <div key={`${name}-${index}`} className="bg-[#f8f6f0] p-2 rounded-lg border border-[#c4c6cd]/30 flex flex-col items-center">
                  <div
                    className="w-8 h-8 rounded-full border border-[#8a8d91] shadow-2xs mb-1 bg-[#f0eee9]"
                    style={color ? { backgroundColor: color } : undefined}
                  ></div>
                  <p className="text-[10px] font-bold text-[#162839]">{name}</p>
                  <span className="text-[9px] text-[#74777d]">{name === '等待沉淀' ? '上传参考 Look' : 'Style DNA'}</span>
                </div>
              );
            })}
          </div>
        </section>

        {/* Keywords & Learning Status */}
        <section className="bg-white p-3.5 rounded-xl border border-[#c4c6cd]/40 shadow-2xs space-y-3">
          <div className="flex justify-between items-center pb-2 border-b border-[#e4e2dd]/60">
            <span className="text-xs font-bold text-[#162839] flex items-center gap-1.5">
              <span className="material-symbols-outlined text-sm text-[#162839]">auto_awesome</span>
              风格关键词与学习状态
            </span>
            <button
              onClick={() => setIsManagingTags(true)}
              className="text-[10px] font-bold text-[#9a442a] bg-[#9a442a]/10 px-2 py-0.5 rounded-full"
            >
              管理标签
            </button>
          </div>

          <div>
            <div className="flex flex-wrap gap-1.5 mb-2">
              {coreTags.length ? coreTags.map((tag) => (
                <span key={tag} className="bg-[#f0eee9] px-2 py-0.5 text-[11px] font-medium text-[#162839] rounded-md">
                  {tag}
                </span>
              )) : <span className="text-[10px] text-[#74777d]">上传参考 Look 后会沉淀核心风格</span>}
            </div>
            {recentSignals.length > 0 && (
              <div className="pt-2 border-t border-[#e4e2dd]/60">
                <p className="text-[10px] text-[#74777d] mb-1">最近风格信号</p>
                <div className="flex flex-wrap gap-1.5">
                  {recentSignals.map((tag) => (
                    <span key={tag} className="border border-[#9a442a]/30 text-[#9a442a] px-2 py-0.5 text-[10px] font-medium rounded-md">
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="pt-1 text-[10px] text-[#43474c] font-medium">
            {ratingCount === 0 ? "正在学习" : `已根据 ${ratingCount} 次反馈更新`}
          </div>
        </section>

        {/* AI Taste Learning Memo / 品味学习备忘录 */}
        <section className="bg-white p-3.5 rounded-xl border border-[#c4c6cd]/40 shadow-2xs space-y-3">
          <div className="flex justify-between items-start pb-2 border-b border-[#e4e2dd]/60">
            <div>
              <div className="flex items-center gap-1.5">
                <span className="material-symbols-outlined text-sm text-[#9a442a]">psychology</span>
                <h3 className="text-xs font-bold text-[#162839]">AI 品味学习备忘录</h3>
                <span className="bg-[#9a442a]/10 text-[#9a442a] text-[9px] px-1.5 py-0.2 rounded-full font-bold font-mono">
                  {ratingCount} 条
                </span>
              </div>
              <p className="text-[10px] text-[#74777d] mt-0.5">查看及修改你的历史打分与 AI 搭配调整意见</p>
            </div>
            <button
              onClick={() => setModalType('ratings')}
              className="text-[11px] font-bold text-[#9a442a] hover:underline flex items-center gap-0.5 shrink-0"
            >
              管理全部
              <span className="material-symbols-outlined text-xs">chevron_right</span>
            </button>
          </div>

          {/* Grouped List Cards for Ratings */}
          <div className="space-y-2.5">
            {ratingList.length > 0 ? (
              ratingList.map((item) => {
                const imgUrl = getLookImageUrl(item);
                return (
                  <div
                    key={item.lookId}
                    onClick={() => setEditingRating(item)}
                    className="bg-[#f8f6f0] p-2.5 rounded-lg border border-[#c4c6cd]/40 hover:border-[#9a442a]/50 cursor-pointer transition-all flex gap-2.5 items-start shadow-2xs group"
                  >
                    <TotalLookThumbnails items={item.lookItems} fallback={imgUrl} alt={item.lookTitle} />

                    {/* Right Content */}
                    <div className="min-w-0 flex-1 space-y-1">
                      <div className="flex justify-between items-start gap-1">
                        <div className="min-w-0">
                          <h4 className="text-xs font-bold text-[#162839] truncate">{item.lookTitle}</h4>
                          <span className="text-[9px] text-[#74777d] font-mono block mt-0.2">{item.timestamp}</span>
                        </div>
                        <div className="flex flex-col items-end shrink-0">
                          <span className="text-[#9a442a] text-xs font-bold tracking-tight">
                            {'★'.repeat(item.rating)}
                            <span className="text-[#c4c6cd]">{'☆'.repeat(5 - item.rating)}</span>
                          </span>
                          <span className="text-[9px] text-[#9a442a] font-bold border border-[#9a442a]/30 px-1.5 py-0.2 rounded mt-0.5 bg-white">
                            修改
                          </span>
                        </div>
                      </div>

                      {/* AI Adjustment Rule */}
                      <div className="bg-[#162839]/5 p-1.5 rounded border border-[#162839]/10 text-[10px] text-[#162839] font-medium leading-tight flex items-start gap-1">
                        <span className="material-symbols-outlined text-xs text-[#9a442a] shrink-0">auto_awesome</span>
                        <span className="line-clamp-2">{item.aiAdjustment}</span>
                      </div>

                      {/* Tags */}
                      {item.tags && item.tags.length > 0 && (
                        <div className="flex flex-wrap gap-1 pt-0.5">
                          {item.tags.map((tag, idx) => (
                            <span
                              key={idx}
                              className="bg-white border border-[#c4c6cd]/30 text-[#43474c] text-[9px] font-medium px-1.5 py-0.2 rounded"
                            >
                              {tag}
                            </span>
                          ))}
                        </div>
                      )}

                      {/* Comment */}
                      {item.comment && (
                        <p className="text-[9px] text-[#43474c] bg-white p-1 rounded border border-[#c4c6cd]/20 line-clamp-1">
                          “{item.comment}”
                        </p>
                      )}
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="p-3 bg-[#f8f6f0] border border-[#c4c6cd]/30 text-center rounded-lg space-y-1">
                <p className="text-xs font-bold text-[#162839]">暂无打分记录</p>
                <p className="text-[10px] text-[#74777d]">在【今日推荐】打分反馈后，AI 会在此记录并指导后续出装！</p>
              </div>
            )}

            <button
              onClick={() => setModalType('ratings')}
              className="w-full py-2 text-center text-[11px] font-bold text-[#162839] bg-[#f0eee9] hover:bg-[#e4e2dd] transition-colors rounded-lg border border-[#c4c6cd]/30 mt-1"
            >
              管理与修改全部 {ratingCount} 条反馈记录 →
            </button>
          </div>
        </section>

        {/* Quick Access Menu List */}
        <section className="bg-white rounded-xl border border-[#c4c6cd]/40 shadow-2xs overflow-hidden divide-y divide-[#e4e2dd]/60">
          <button
            onClick={() => setModalType('ratings')}
            className="w-full flex justify-between items-center p-3 text-left hover:bg-[#f8f6f0] transition-colors"
          >
            <div className="flex items-center gap-2.5">
              <span className="material-symbols-outlined text-sm text-[#9a442a]">auto_awesome</span>
              <span className="text-xs font-bold text-[#162839]">AI 品味反馈与打分历史</span>
            </div>
            <div className="flex items-center gap-1">
              <span className="text-[10px] font-bold text-[#9a442a] bg-[#9a442a]/10 px-1.5 py-0.5 rounded font-mono">
                {ratingCount} 条
              </span>
              <span className="material-symbols-outlined text-xs text-[#74777d]">chevron_right</span>
            </div>
          </button>

          <button
            onClick={() => setModalType('history')}
            className="w-full flex justify-between items-center p-3 text-left hover:bg-[#f8f6f0] transition-colors"
          >
            <div className="flex items-center gap-2.5">
              <span className="material-symbols-outlined text-sm text-[#162839]">history</span>
              <span className="text-xs font-bold text-[#162839]">每日穿搭推荐历史</span>
            </div>
            <div className="flex items-center gap-1">
              <span className="text-[10px] font-bold text-[#162839] bg-[#162839]/10 px-1.5 py-0.5 rounded font-mono">
                {historyList.length} 方案
              </span>
              <span className="material-symbols-outlined text-xs text-[#74777d]">chevron_right</span>
            </div>
          </button>

          <button
            onClick={() => setModalType('favorites')}
            className="w-full flex justify-between items-center p-3 text-left hover:bg-[#f8f6f0] transition-colors"
          >
            <div className="flex items-center gap-2.5">
              <span className="material-symbols-outlined text-sm text-[#9a442a]">bookmark</span>
              <span className="text-xs font-bold text-[#162839]">我的灵感收藏</span>
            </div>
            <div className="flex items-center gap-1">
              <span className="text-[10px] font-bold text-[#9a442a] bg-[#9a442a]/10 px-1.5 py-0.5 rounded font-mono">
                {favoritesList.length} 套
              </span>
              <span className="material-symbols-outlined text-xs text-[#74777d]">chevron_right</span>
            </div>
          </button>

          <button
            onClick={() => setModalType('settings')}
            className="w-full flex justify-between items-center p-3 text-left hover:bg-[#f8f6f0] transition-colors"
          >
            <div className="flex items-center gap-2.5">
              <span className="material-symbols-outlined text-sm text-[#162839]">settings</span>
              <span className="text-xs font-bold text-[#162839]">应用与引擎偏好</span>
            </div>
            <span className="material-symbols-outlined text-xs text-[#74777d]">chevron_right</span>
          </button>
        </section>
      </main>

      {/* Edit Profile ID Modal */}
      {isEditing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4">
          <div className="bg-[#fbf9f4] p-5 max-w-xs w-full border border-[#162839] relative rounded-xl shadow-lg">
            <h3 className="text-sm font-bold text-[#162839] mb-3">修改 Style ID</h3>
            <input
              type="text"
              value={styleId}
              onChange={(e) => setStyleId(e.target.value)}
              className="w-full p-2 border border-[#c4c6cd] bg-white text-xs mb-4 text-[#162839] rounded-lg"
            />
            <button
              onClick={() => setIsEditing(false)}
              className="w-full bg-[#162839] text-white py-2 text-xs font-bold rounded-lg"
            >
              保存修改
            </button>
          </div>
        </div>
      )}

      {/* Editing Specific Rating Modal */}
      {editingRating && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4">
          <div className="bg-[#fbf9f4] p-4 max-w-xs w-full border border-[#162839] relative rounded-xl shadow-xl max-h-[85vh] flex flex-col">
            <div className="flex justify-between items-center mb-2 pb-2 border-b border-[#c4c6cd]/40">
              <h3 className="text-xs font-bold text-[#162839]">修改评分与微调意见</h3>
              <button onClick={() => setEditingRating(null)} className="text-[#74777d] hover:text-[#162839] p-1">
                <span className="material-symbols-outlined text-base">close</span>
              </button>
            </div>

            <div className="overflow-y-auto space-y-3 my-2 flex-1 pr-1">
              <div className="flex items-center gap-2.5 bg-white p-2 rounded-lg border border-[#c4c6cd]/40">
                <img
                  src={getLookImageUrl(editingRating)}
                  alt={editingRating.lookTitle}
                  className="w-12 h-16 object-cover rounded border border-[#c4c6cd]/30 shrink-0"
                />
                <div className="min-w-0">
                  <p className="text-xs font-bold text-[#162839] leading-snug">{editingRating.lookTitle}</p>
                  <p className="text-[10px] text-[#74777d] font-mono mt-0.5">{editingRating.timestamp}</p>
                </div>
              </div>

              {/* Star rating selector */}
              <div>
                <label className="text-[10px] text-[#74777d] font-bold block mb-1">星级打分</label>
                <div className="flex gap-2 text-2xl text-[#9a442a]">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <button
                      key={star}
                      onClick={() => setEditingRating({ ...editingRating, rating: star })}
                      className="hover:scale-110 transition-transform"
                    >
                      {star <= editingRating.rating ? '★' : '☆'}
                    </button>
                  ))}
                </div>
              </div>

              {/* Tags */}
              <div>
                <label className="text-[10px] text-[#74777d] font-bold block mb-1">选择反馈标签</label>
                <div className="flex flex-wrap gap-1">
                  {RATING_TAG_OPTIONS.map((tag) => {
                    const isSel = editingRating.tags.includes(tag);
                    return (
                      <button
                        key={tag}
                        onClick={() => {
                          const newTags = isSel
                            ? editingRating.tags.filter((t) => t !== tag)
                            : [...editingRating.tags, tag];
                          setEditingRating({ ...editingRating, tags: newTags });
                        }}
                        className={`text-[10px] px-2 py-0.5 rounded-md font-medium transition-all ${
                          isSel ? 'bg-[#9a442a] text-white' : 'bg-[#e4e2dd] text-[#162839]'
                        }`}
                      >
                        {tag}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Comments */}
              <div>
                <label className="text-[10px] text-[#74777d] font-bold block mb-1">补充文字建议</label>
                <textarea
                  value={editingRating.comment || ''}
                  onChange={(e) => setEditingRating({ ...editingRating, comment: e.target.value })}
                  placeholder="例如：衬衫面料希望能更挺括一些..."
                  className="w-full text-xs p-2 border border-[#c4c6cd] bg-white rounded-lg text-[#162839] h-16 resize-none"
                />
              </div>
            </div>

            <div className="flex gap-2 pt-2 border-t border-[#c4c6cd]/40">
              <button onClick={() => setEditingRating(null)} className="border border-[#162839]/30 text-[#162839] text-xs font-bold py-2 px-3 rounded-lg">
                取消
              </button>
              <button
                onClick={() => saveUpdatedRating(editingRating)}
                className="flex-1 bg-[#162839] text-white text-xs font-bold py-2 rounded-lg hover:opacity-90 transition-opacity"
              >
                保存更新
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Link Modals */}
      {modalType && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4">
          <div className="bg-[#fbf9f4] p-4 max-w-xs w-full border border-[#162839] relative rounded-xl max-h-[80vh] flex flex-col shadow-xl">
            <div className="flex justify-between items-center mb-2 pb-2 border-b border-[#c4c6cd]/40">
              <h3 className="text-xs font-bold text-[#162839] uppercase tracking-wider">
                {modalType === 'ratings' && 'AI 品味学习历史与评分编辑'}
                {modalType === 'history' && '每日推荐历史记录'}
                {modalType === 'favorites' && '我的灵感收藏'}
                {modalType === 'settings' && '应用与引擎设置'}
              </h3>
              <button onClick={() => setModalType(null)} className="text-[#74777d] p-1">
                <span className="material-symbols-outlined text-base">close</span>
              </button>
            </div>

            {modalType === 'ratings' && (
              <div className="overflow-y-auto my-2 space-y-2.5 flex-1 pr-1">
                {ratingList.length > 0 ? (
                  ratingList.map((item) => {
                    const imgUrl = getLookImageUrl(item);
                    return (
                      <div key={item.lookId} className="bg-[#f5f3ee] p-2.5 rounded-lg border border-[#c4c6cd]/40 flex gap-2.5 items-start">
                        <img
                          src={imgUrl}
                          alt={item.lookTitle}
                          className="w-13 h-16 object-cover rounded-md border border-[#c4c6cd]/40 bg-white shrink-0"
                          onError={(e) => {
                            (e.target as HTMLImageElement).src = IMAGE_FALLBACKS.safe;
                          }}
                        />
                        <div className="min-w-0 flex-1 space-y-1">
                          <div className="flex justify-between items-start">
                            <h4 className="font-bold text-xs text-[#162839] truncate">{item.lookTitle}</h4>
                            <span className="text-[#9a442a] text-xs font-bold shrink-0 ml-1">
                              {'★'.repeat(item.rating)}
                            </span>
                          </div>
                          <p className="text-[10px] text-[#9a442a] font-medium leading-snug">{item.aiAdjustment}</p>
                          {item.tags.length > 0 && (
                            <div className="flex flex-wrap gap-1">
                              {item.tags.map((t, idx) => (
                                <span key={idx} className="bg-[#9a442a]/10 text-[#9a442a] text-[9px] px-1.5 py-0.2 rounded font-bold">
                                  {t}
                                </span>
                              ))}
                            </div>
                          )}
                          {item.comment && (
                            <p className="text-[9px] text-[#43474c] bg-white p-1 rounded border border-[#c4c6cd]/20">
                              “{item.comment}”
                            </p>
                          )}
                          <div className="flex justify-between items-center pt-1 border-t border-[#c4c6cd]/30 mt-1">
                            <span className="text-[9px] text-[#74777d] font-mono">{item.timestamp}</span>
                            <button
                              onClick={() => setEditingRating(item)}
                              className="text-[10px] text-[#9a442a] font-bold underline hover:opacity-80"
                            >
                              修改评分/微调
                            </button>
                          </div>
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <p className="text-xs text-[#43474c] text-center py-6">
                    暂无评分反馈记录。去【今日推荐】页面打分，教 AI 懂你穿搭！
                  </p>
                )}
              </div>
            )}

            {modalType === 'favorites' && (
              <div className="overflow-y-auto my-2 space-y-2.5 flex-1 pr-1">
                {favoritesList.length > 0 ? (
                  favoritesList.map((item) => {
                    const items = item.lookItems || [
                      { name: item.description?.split('+')[0]?.trim() || '主要上装', category: '上装', img: item.imageUrl },
                      { name: item.description?.split('+')[1]?.trim() || '搭配下装', category: '下装', img: 'https://images.unsplash.com/photo-1594633312681-425c7b97ccd1?w=300&auto=format&fit=crop&q=80' },
                      { name: item.description?.split('+')[2]?.trim() || '精选鞋履', category: '鞋履', img: 'https://images.unsplash.com/photo-1549298916-b41d501d3772?w=300&auto=format&fit=crop&q=80' }
                    ];

                    return (
                      <div key={item.id} className="bg-[#f5f3ee] p-2.5 rounded-lg border border-[#c4c6cd]/40">
                        <div className="flex justify-between items-start mb-1.5">
                          <div>
                            <div className="flex items-center gap-1.5">
                              <h4 className="text-xs font-bold text-[#162839]">{item.title}</h4>
                              <span className="bg-[#9a442a]/10 text-[#9a442a] text-[9px] font-mono px-1.5 py-0.2 rounded font-bold">
                                {item.tag}
                              </span>
                            </div>
                            <p className="text-[9px] text-[#74777d] font-mono">收藏于 {item.dateAdded || '今日'}</p>
                          </div>
                          <button
                            onClick={() => removeFavorite(item.id)}
                            className="text-[#9a442a] hover:opacity-70 p-1"
                            title="取消收藏"
                          >
                            <span className="material-symbols-outlined text-sm">delete</span>
                          </button>
                        </div>

                        <div className="bg-white p-1.5 rounded-md border border-[#c4c6cd]/30 mb-1">
                          <div className="grid grid-cols-3 gap-1.5">
                            {items.map((sub, idx) => (
                              <div key={idx} className="flex flex-col items-center text-center">
                                <div className="w-full aspect-square overflow-hidden rounded bg-[#fbf9f4] border border-[#c4c6cd]/40 relative">
                                  <img
                                    src={sub.img}
                                    alt={sub.name}
                                    className="w-full h-full object-cover"
                                    onError={(e) => {
                                      const target = e.target as HTMLImageElement;
                                      target.src = 'https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=300&auto=format&fit=crop&q=80';
                                    }}
                                  />
                                </div>
                                <p className="text-[9px] text-[#162839] font-medium mt-0.5 line-clamp-1 w-full">
                                  {sub.name}
                                </p>
                              </div>
                            ))}
                          </div>
                        </div>

                        {item.description && (
                          <p className="text-[9px] text-[#43474c] bg-[#e4e2dd]/40 p-1 rounded font-mono">
                            搭配：{item.description}
                          </p>
                        )}
                      </div>
                    );
                  })
                ) : (
                  <div className="text-center py-6 px-2">
                    <span className="material-symbols-outlined text-2xl text-[#74777d] mb-1">bookmark_border</span>
                    <p className="text-xs text-[#43474c]">你尚未收藏任何 Look 方案。</p>
                  </div>
                )}
              </div>
            )}

            {modalType === 'history' && (
              <div className="overflow-y-auto my-2 space-y-2.5 flex-1 pr-1">
                {historyList.length > 0 ? (
                  historyList.map((hist) => (
                    <div key={hist.id} className="bg-[#f5f3ee] p-2.5 rounded-lg border border-[#c4c6cd]/40">
                      <div className="flex justify-between items-center mb-1">
                        <span className="text-[10px] font-mono text-[#9a442a] font-bold">{hist.date}</span>
                        <span className="bg-[#162839]/10 text-[#162839] text-[9px] px-1.5 py-0.2 rounded font-bold">
                          {hist.tag}
                        </span>
                      </div>
                      <h4 className="text-xs font-bold text-[#162839] mb-1">{hist.title}</h4>

                      <div className="grid grid-cols-3 gap-1 bg-white p-1 rounded-md border border-[#c4c6cd]/30 mb-1">
                        {hist.items.map((sub, i) => (
                          <div key={i} className="text-center">
                            <img
                              src={sub.img}
                              alt={sub.name}
                              className="w-full h-10 object-cover rounded border border-[#c4c6cd]/30 bg-[#fbf9f4]"
                            />
                            <span className="text-[8px] text-[#43474c] block truncate mt-0.5">{sub.name}</span>
                          </div>
                        ))}
                      </div>
                      <p className="text-[9px] text-[#43474c]">{hist.description}</p>
                      <div className="mt-2 flex flex-wrap gap-1">
                        <span className="text-[9px] text-[#74777d] border border-[#c4c6cd]/40 px-1.5 py-0.5 rounded">{hist.scope === 'archive' ? '存档' : '近期'}</span>
                        <button onClick={() => void updateHistoryAction(hist, hist.action === 'saved' ? 'shown' : 'saved')} className="text-[9px] text-[#9a442a] border border-[#9a442a]/30 px-1.5 py-0.5 rounded">
                          {hist.action === 'saved' ? '取消收藏' : '收藏'}
                        </button>
                        <button onClick={() => setEditingRating({
                          lookId: hist.id,
                          historyId: hist.historyId,
                          lookTitle: hist.title,
                          rating: hist.rating || 5,
                          tags: [],
                          timestamp: hist.date,
                          aiAdjustment: '已同步到 AI 品味备忘录',
                          lookImage: hist.imageUrl,
                          lookItems: hist.lookItems,
                        })} className="text-[9px] text-[#162839] border border-[#162839]/30 px-1.5 py-0.5 rounded">{hist.rating ? `${hist.rating}★` : '评分'}</button>
                        <button onClick={() => void updateHistoryAction(hist, 'worn')} className="text-[9px] text-[#162839] border border-[#162839]/30 px-1.5 py-0.5 rounded">{hist.woreIt ? '已穿着' : '标记穿过'}</button>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-[#43474c] text-center py-6">
                    暂无历史推荐记录。
                  </p>
                )}
              </div>
            )}

            {modalType === 'settings' && (
              <div className="py-4 text-xs text-[#43474c] space-y-2">
                <p>· 已开启深色模式适配与 AI 自动日杂调色引擎。</p>
                <p>· 当前推荐模式：3档对比推荐 (SAFE / FRESH / STRETCH)。</p>
                <p>· 当前引擎版本：v2.4.0 (Build 894-FX)。</p>
              </div>
            )}

            <button
              onClick={() => setModalType(null)}
              className="w-full bg-[#162839] text-white py-1.5 text-xs font-bold rounded-lg mt-2"
            >
              关闭
            </button>
          </div>
        </div>
      )}

      {isManagingTags && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4">
          <div className="bg-[#fbf9f4] p-4 max-w-xs w-full border border-[#162839] rounded-xl max-h-[80vh] flex flex-col shadow-xl">
            <div className="flex justify-between items-center mb-2 pb-2 border-b border-[#c4c6cd]/40">
              <div>
                <h3 className="text-xs font-bold text-[#162839]">管理标签</h3>
                <p className="text-[9px] text-[#74777d]">置顶最多 3 个；隐藏仅影响摘要展示</p>
              </div>
              <button onClick={() => setIsManagingTags(false)} className="text-[#74777d] p-1" aria-label="关闭标签管理">
                <span className="material-symbols-outlined text-base">close</span>
              </button>
            </div>

            {isMergingTags ? (
              <div className="space-y-2 overflow-y-auto">
                <p className="text-[10px] text-[#43474c]">选择恰好两个标签，再填写一个统一名称。</p>
                {allTags.map((tag) => (
                  <button
                    key={tag}
                    onClick={() => toggleMergeTag(tag)}
                    className={`w-full flex justify-between items-center p-2 rounded-lg border text-left text-[11px] ${mergeTags.includes(tag) ? 'border-[#9a442a] bg-[#9a442a]/10 text-[#9a442a]' : 'border-[#c4c6cd]/40 bg-white text-[#162839]'}`}
                  >
                    <span>{normalizeTag(tag)}</span>
                    {mergeTags.includes(tag) && <span className="material-symbols-outlined text-sm">check</span>}
                  </button>
                ))}
                <input
                  value={mergeName}
                  onChange={(event) => setMergeName(event.target.value)}
                  placeholder="统一名称"
                  className="w-full p-2 border border-[#c4c6cd] bg-white text-xs text-[#162839] rounded-lg"
                />
                <div className="flex gap-2">
                  <button
                    onClick={() => { setIsMergingTags(false); setMergeTags([]); setMergeName(''); }}
                    className="flex-1 border border-[#162839]/30 text-[#162839] py-2 text-xs font-bold rounded-lg"
                  >
                    取消
                  </button>
                  <button onClick={confirmMerge} className="flex-1 bg-[#162839] text-white py-2 text-xs font-bold rounded-lg">
                    确认合并
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-2 overflow-y-auto">
                {allTags.length ? allTags.map((tag) => {
                  const isPinned = (tagPreferences.pinned || []).includes(tag);
                  const isHidden = (tagPreferences.hidden || []).includes(tag);
                  return (
                    <div key={tag} className="bg-white p-2 rounded-lg border border-[#c4c6cd]/40 flex items-center gap-2">
                      <span className="text-[11px] text-[#162839] font-medium flex-1 min-w-0 truncate">{normalizeTag(tag)}</span>
                      <button onClick={() => togglePinnedTag(tag)} className="text-[10px] text-[#162839] border border-[#162839]/30 px-1.5 py-1 rounded">
                        {isPinned ? '取消置顶' : '置顶'}
                      </button>
                      <button onClick={() => toggleHiddenTag(tag)} className="text-[10px] text-[#9a442a] border border-[#9a442a]/30 px-1.5 py-1 rounded">
                        {isHidden ? '恢复' : '隐藏'}
                      </button>
                    </div>
                  );
                }) : <p className="text-xs text-[#74777d] text-center py-4">还没有可管理的风格标签</p>}
                <button
                  onClick={() => setIsMergingTags(true)}
                  className="w-full border border-[#162839]/30 text-[#162839] py-2 text-xs font-bold rounded-lg"
                >
                  合并标签
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {tagError && (
        <div role="alert" className="fixed z-[60] bottom-24 inset-x-4 max-w-md mx-auto bg-[#162839] text-white px-3 py-2 rounded-lg shadow-lg text-[11px] flex justify-between gap-2">
          <span>{tagError}</span>
          <button onClick={() => setTagError('')} aria-label="关闭提示">×</button>
        </div>
      )}

      {/* Bottom Navigation Bar */}
      <BottomNav currentScreen="profile" onNavigate={onNavigate} />
    </div>
  );
};
