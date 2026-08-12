import React, { useEffect, useState } from 'react';
import { ScreenId, InspirationItem } from '../types';
import { api } from '../lib/api.mjs';
import { BottomNav } from './BottomNav';
import { SideDrawer } from './SideDrawer';

interface ScreenArchiveProps {
  onNavigate: (screen: ScreenId) => void;
}

const ARCHIVE_ITEMS: InspirationItem[] = [
  {
    id: '1',
    title: 'City Sunset Streetstyle',
    category: 'Casual',
    imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBnr6IQtadzxhFu3_VguFCc6t5TO15CA9jGnbKTqOhi6R9Az7jcNWqHt-D7Gh8tL-x2ZRzHZQ9NOTs4l1rgUVZWHyZTs41fJdjDxR1FVGFCGZGPSvt_LIJElG0dVYz56ga9U3eIoBr9tt7ezwuwEl-AedhPjdtj726FcdiWUkFvSCEqN1YKxXx3uOLKJFlDagP2mDUAfeBBuNxIj6HAzEMnN9xvPg1JK3j93MRgcrvebxuH6ZM0CLF8',
    tags: ['#Casual', '#Orange']
  },
  {
    id: '2',
    title: 'Ivy Style Trench Layering',
    category: 'IvyStyle',
    imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuC18NBg_KXnEdXRsQepIDSSJb9GeIizAGMZ8XSKWTrMGrGc0HCBP3RHeOpjumEg3nR9SjOro5VFO_EA4P7t0ETN8M8Xkzc3ZzEZ2vz7xH4ciBGiC_sD-IKvmdoYyVXuWTT3vAWLlif323FrjbbdGdBpwk0QA8DV1A5M5I2jqRB8IeBZr1j558k_MEw8DzrHbY8b9soPOUmeOpjumEg3nR9SjOro5VFO_EA4P7t0ETN8M8Xkzc3ZzEZ2vz7xH4ciBGiC_sD-IKvmdoYyVXuWTT3vAWLlif323FrjbbdGdBpwk0QA8DV1A5M5I2jqRB8IeBZr1j558k_MEw8DzrHbY8b9soPOUmeObmYAU0B7KTVaKAlRXjSmhFLwWz79R3lgUubwsp1nvbk',
    tags: ['#IvyStyle', '#Layering'],
    badge: 'NEW'
  },
  {
    id: '3',
    title: 'Campus Blazer Walk',
    category: 'Preppy',
    imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuAHH58A-Bs2k7pFG61lAMJrRkYqT9ZzLDqS52sF9fOJLVZBj0oTI_B2uoA9N0SYrEVXxGbL3P5rrCZ3odmPCHPlPfihKOhdDCfRtKrx5YQTXl6e_KMYQxTxvGjukcaOBQB2M2Z_RAoC-1nKpo_X5dfeCxT2HfQF5WyAoHodChjM2H-9aTfm4Mc0lVPCPpyj5A3FmWPu20WuZViXKRSxFH0R3fcskCbrI2BtRXuPEAt9L-PBcGFTvUik',
    tags: ['#Blazer', '#Preppy']
  },
  {
    id: '4',
    title: 'Active Green Sweater Movement',
    category: 'Active',
    imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuD2uy0mpvCQDklvNgmmHowL6V8b84gHpvaxOlh2JN4z69eeGSs82YEOsP2Us-MZkx4dEp-7z8szdwboO0FGRNHgzQydwWyVjt6jZ8DsXIq7MwvOtCZ7KWSLMTjrNA4MKwjQJMAb10TfanhO6gNsADNw9atvbW4-9jAa0yKS9wQMz4Sg65l8jxmAAtaLG6YcUvGLkpBxIRejjZNJWMiOBoX7XJqXUTETxD-IwebtiZRAsp0sboby9lSu',
    tags: ['#Active', '#Green']
  },
  {
    id: '5',
    title: 'Relaxed Kitchen Morning',
    category: 'Home',
    imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuAWa-9S4W1d9r9J5s6Hfc13bL_AiHrM6HdDwVPV-1OhyGTaBxNv34Y9BQIrcfTW2fhNWkVgvWSvPephOHCvfbMMn4ONsRtZ8s_4P5HaFeRtMyDZQtgpWRzG7Z_i6EYZanoNaeQoKe7f0oJBZGFtOa2jsU75JmmXXGq6Z31im7gJYwWhcE9gB4dEdseAdTCjYRMi1IX8Q1bnWWwEh6eo3LQFKGliVBYAYILzwTutxFbDPkdSH4fmQ6XW',
    tags: ['#Home', '#Relaxed']
  },
  {
    id: '6',
    title: 'Winter Navy Coat & Denim',
    category: 'Winter',
    imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuAZgrK2jlPTBky2-Fb8OYgbqGVvmZbfzpHWebZrN1MmsopySc-RJ25546WMSc41n54O6Zx2JOIKi-7dFoLCHnjO_nqV_-nwjgjBtoDAfbq9bNkY82wD3uUwvTlbWCmiUZGOC_-GO74yIe3R14prrDiL7I5Xb_QUWj9mikjgTT6Ritt-pxsRiKgo1LrTOKMlVcUH9IF9OsRjvYl0XDnbPXnq7B_NENOS4Wf8d0dql04Hv4xRvXBW8uJF',
    tags: ['#Coat', '#Denim'],
    badge: 'WINTER'
  }
];

const MORE_ARCHIVE_ITEMS: InspirationItem[] = [
  {
    id: 'arch-7',
    title: 'Minimalist Tokyo Coffee Break',
    category: 'Minimal',
    imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBHql_kA1QBu5PdlksjBh57JEYklOBf9QFgGOemLmBKOIcR1_4HYVUfx8__czG7X8xJao48bfq_5Qc9WiKU7vs8zlNs-5QTgdbLuw6s9pkespNnL89bpuEqBv-xyt6lMXV_U6_NyBkZqqFnkkTXwTDK9DdoWOFQS44o0UhL4iNLmv93AlS7xo_xDcT7UbE4-2cbn-uYJ4tOAtGTt3goA9h1iucCnjRKzMK3bdeVtB88eXkop0hCgDRg',
    tags: ['#TokyoStyle', '#Minimal'],
    badge: 'NEW'
  },
  {
    id: 'arch-8',
    title: 'Oversized Blazer & Denim Layering',
    category: 'Casual',
    imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuD78ZO71iiNM0eur0CzpknzuLV0XqwlYB21cOepkGDRlrodTofaveXVw1ojVZ3ZbjI9yKef5JT7jq7x8rX5laZ-MrJWgX8o69FT1Jy0io5eXcK3mgZ_Nthlajrd65PkE1617KvgzW7mj5rVOtZUABPk5fdYtuYjdFCedLQqA20WQCst1fZl2D9W1g1G6aP7AnDwoa633xl4Xa4ad_Up3qn6ZVTlhKoOMlfdChtxyG6eXmEJKvhdklWj',
    tags: ['#Blazer', '#Denim']
  },
  {
    id: 'arch-9',
    title: 'Earthy Tone Tailored Trousers',
    category: 'SmartCasual',
    imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuA-pfIL9b9XBhE2BUt63veY_0rB8R8x2L0nmAtS9a0CgiJc3lcH7mzzgknlYvk4U8jeA242IY4gpj3PJbatQmsm0aF8JtiVZdhOh7EKsZyzJSTHCwhlz328vlCJBZAHiR8Ams_H-7TH5Y6Ge4pwV8EXJk1vl13N_n3rzU2EVPwWYPGtAue-wyU1r9SAAB51AEOKDw-qsbbRyvpTn3n3w7l7Q-1Moned4n2X1a3ERWCCU_LQo28FzECX',
    tags: ['#EarthTone', '#Trousers']
  },
  {
    id: 'arch-10',
    title: 'Chunky Knit & Loafers Ensemble',
    category: 'Autumn',
    imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuAN-vdwTEbVAujzyoBX7uIMHV9bkCM_LXhzfKJcXTYcfLA5h7rIDCmaV6Pj98BAaCjURMJR-fgUe3chDKgbCCbWQzw5ElvQS2MwBej4bX2ZkNNyeD8xji_miQIM1jzaMTpRxHiCbKoTe9V524eAGMU1I7ddUgdDbkATGdQFuNS7oLHEITmf289th8ZJkbDCU_tibwfu9ft0F5vCqk9D6LtJsP2tVyp4p9Ae1c4bzyVqlSLRLmAJZQXr',
    tags: ['#ChunkyKnit', '#Loafers']
  },
  {
    id: 'arch-11',
    title: 'Contemporary Workwear Jacket',
    category: 'Workwear',
    imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBuRUKU2ptL8Ug55H8Zc8CuPihQ7OQ9rzIVjv1mcpJmtdT7v9dYNc1xgKxavZl-rFOCr8waLbcjC1bxY-pe3IUW3z8Y6z5wlvPRhqPpqDAo3RQWG50r3gk-FrQx4bq4vqL8zNQznl1UbMPiPAox_3ToAiKWnKld1RtRcgJaG-TF35WHoYESsnP0ra_F6NxujGy8Ca-qcRZhWWc022XrzI2znI_UdaRbkFnCP5ZJJ1GnbFjS9xlPApFw',
    tags: ['#Workwear', '#Vintage']
  },
  {
    id: 'arch-12',
    title: 'Monochrome Urban Silhouette',
    category: 'Monochrome',
    imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuC18NBg_KXnEdXRsQepIDSSJb9GeIizAGMZ8XSKWTrMGrGc0HCBP3RHeOpjumEg3nR9SjOro5VFO_EA4P7t0ETN8M8Xkzc3ZzEZ2vz7xH4ciBGiC_sD-IKvmdoYyVXuWTT3vAWLlif323FrjbbdGdBpwk0QA8DV1A5M5I2jqRB8IeBZr1j558k_MEw8DzrHbY8b9soPOUmeOpjumEg3nR9SjOro5VFO_EA4P7t0ETN8M8Xkzc3ZzEZ2vz7xH4ciBGiC_sD-IKvmdoYyVXuWTT3vAWLlif323FrjbbdGdBpwk0QA8DV1A5M5I2jqRB8IeBZr1j558k_MEw8DzrHbY8b9soPOUmeObmYAU0B7KTVaKAlRXjSmhFLwWz79R3lgUubwsp1nvbk',
    tags: ['#Monochrome', '#Urban']
  }
];

export const ScreenArchive: React.FC<ScreenArchiveProps> = ({ onNavigate }) => {
  const [items, setItems] = useState<InspirationItem[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [isManaging, setIsManaging] = useState<boolean>(false);
  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(false);
  const [activeTag, setActiveTag] = useState<string | null>(null);
  const [previewItem, setPreviewItem] = useState<InspirationItem | null>(null);
  const [isLoadingMore, setIsLoadingMore] = useState<boolean>(false);
  const [hasMore, setHasMore] = useState<boolean>(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const triggerToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  useEffect(() => {
    api.references()
      .then(setItems)
      .catch((error: unknown) => triggerToast(error instanceof Error ? error.message : '灵感库加载失败'));
  }, []);

  const toggleSelect = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (selectedIds.includes(id)) {
      setSelectedIds(selectedIds.filter(item => item !== id));
    } else {
      setSelectedIds([...selectedIds, id]);
    }
  };

  const handleDelete = async () => {
    if (selectedIds.length === 0) return;
    try {
      await Promise.all(selectedIds.map((id) => api.deleteReference(id)));
      setItems(items.filter(item => !selectedIds.includes(item.id)));
      setSelectedIds([]);
      triggerToast('已删除选中的灵感画报');
    } catch (error) {
      triggerToast(error instanceof Error ? error.message : '删除失败');
    }
  };

  const handleLoadMore = () => {
    setIsLoadingMore(true);
    setTimeout(() => {
      setItems(prev => [...prev, ...MORE_ARCHIVE_ITEMS]);
      setIsLoadingMore(false);
      setHasMore(false);
      triggerToast('✨ 已成功加载一屏全新灵感画报 (共 6 张)');
    }, 700);
  };

  const filteredItems = activeTag
    ? items.filter(i => i.tags.includes(activeTag))
    : items;

  return (
    <div className="bg-[#fbf9f4] text-[#1b1c19] min-h-screen flex flex-col pb-24 md:pb-0">
      {/* Side Drawer Menu */}
      <SideDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        currentScreen="archive"
        onNavigate={onNavigate}
      />

      {/* TopAppBar */}
      <header className="bg-[#fbf9f4] border-b border-[#c4c6cd]/40 sticky top-0 z-40">
        <div className="flex justify-between items-center px-6 h-16 max-w-lg mx-auto">
          <div className="flex items-center gap-2">
            <button onClick={() => setIsDrawerOpen(true)} className="text-[#162839] hover:opacity-80 flex items-center justify-center p-2 rounded hover:bg-[#f0eee9]" title="打开侧边导航">
              <span className="material-symbols-outlined text-[22px]">menu</span>
            </button>
            <button onClick={() => onNavigate('inspiration')} className="text-[#162839] hover:opacity-80 flex items-center justify-center p-2 rounded hover:bg-[#f0eee9]" title="灵感网格">
              <span className="material-symbols-outlined text-[20px]">grid_view</span>
            </button>
          </div>
          <div className="font-serif-display font-bold text-[#162839] text-xl flex-1 text-center md:text-left ml-2">
            Outfit-AI
          </div>

          {/* Desktop Nav Cluster */}
          <nav className="hidden md:flex gap-8 items-center mr-8">
            <a
              href="#"
              onClick={(e) => { e.preventDefault(); onNavigate('today'); }}
              className="text-[#9a442a] hover:opacity-80 text-xs font-semibold uppercase tracking-wider transition-colors"
            >
              <span>今日</span>
            </a>
            <a
              href="#"
              onClick={(e) => { e.preventDefault(); onNavigate('wardrobe'); }}
              className="text-[#9a442a] hover:opacity-80 text-xs font-semibold uppercase tracking-wider transition-colors"
            >
              <span>衣橱</span>
            </a>
            <a
              href="#"
              onClick={(e) => { e.preventDefault(); onNavigate('inspiration'); }}
              className="text-[#162839] hover:opacity-80 text-xs font-bold uppercase tracking-wider transition-colors border-b-2 border-[#162839] pb-0.5"
            >
              <span>灵感</span>
            </a>
            <a
              href="#"
              onClick={(e) => { e.preventDefault(); onNavigate('profile'); }}
              className="text-[#9a442a] hover:opacity-80 text-xs font-semibold uppercase tracking-wider transition-colors"
            >
              <span>我的</span>
            </a>
          </nav>

          <button className="text-[#162839] hover:opacity-80 flex items-center justify-center p-2">
            <span className="material-symbols-outlined">wb_sunny</span>
          </button>
        </div>
      </header>

      {/* Main Content Canvas */}
      <main className="flex-1 max-w-lg mx-auto w-full px-4 py-6">
        {/* Header Section */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-end mb-8 gap-4 relative">
          <div>
            <div className="washi-tape top-[-12px] left-[-4px]">Archive</div>
            <h1 className="font-serif-display text-2xl md:text-3xl text-[#162839] mb-1 mt-3 tracking-wider font-bold">
              灵感存档
            </h1>
            <p className="text-xs text-[#43474c]">共 {items.length} 张精选图片</p>
          </div>

          {/* Action Bar */}
          <div className="flex items-center gap-4 bg-[#eae8e3] py-2 px-4 rounded-none w-full md:w-auto justify-between md:justify-start">
            <button
              onClick={() => setIsManaging(!isManaging)}
              className={`flex items-center gap-2 text-xs uppercase tracking-wider font-semibold ${
                isManaging ? 'text-[#9a442a]' : 'text-[#162839]'
              }`}
            >
              <span className="material-symbols-outlined text-[18px]">checklist</span>
              {isManaging ? '完成选择' : '批量管理'}
            </button>
            <div className="w-px h-4 bg-[#c4c6cd]"></div>
            <button
              onClick={handleDelete}
              disabled={selectedIds.length === 0}
              className={`flex items-center gap-2 text-xs uppercase tracking-wider font-semibold ${
                selectedIds.length > 0 ? 'text-[#ba1a1a] cursor-pointer' : 'text-[#ba1a1a]/40 cursor-not-allowed'
              }`}
            >
              <span className="material-symbols-outlined text-[18px]">delete</span>
              删除 ({selectedIds.length})
            </button>
          </div>
        </div>

        {/* Toast Notification */}
        {toastMessage && (
          <div className="fixed top-20 left-1/2 -translate-x-1/2 z-50 bg-[#162839] text-white px-5 py-2.5 rounded shadow-xl text-xs font-medium border border-white/20 animate-fade-in flex items-center gap-2">
            <span className="material-symbols-outlined text-[#f4dfcb] text-base">check_circle</span>
            {toastMessage}
          </div>
        )}

        {/* Tag Filters */}
        {activeTag && (
          <div className="mb-6 flex items-center gap-2">
            <span className="text-xs text-[#43474c]">筛选标签:</span>
            <span className="bg-[#162839] text-white text-xs px-2.5 py-1 flex items-center gap-1">
              {activeTag}
              <button onClick={() => setActiveTag(null)} className="ml-1 font-bold">×</button>
            </span>
          </div>
        )}

        {/* Contact Sheet Grid */}
        <div className="grid grid-cols-3 md:grid-cols-4 gap-2 md:gap-4">
          {filteredItems.map((item) => {
            const isSelected = selectedIds.includes(item.id);
            return (
              <div
                key={item.id}
                onClick={() => isManaging ? null : setPreviewItem(item)}
                className="relative group cursor-pointer min-w-0"
              >
                {(isManaging || isSelected) && (
                  <div
                    onClick={(e) => toggleSelect(item.id, e)}
                    className="absolute top-1 right-1 z-20"
                  >
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => {}}
                      className="w-4 h-4 md:w-5 md:h-5 accent-[#162839] cursor-pointer"
                    />
                  </div>
                )}

                <div className="bg-[#f5f3ee] p-1.5 md:p-2.5 md:pb-8 relative contact-shadow border border-[#e4e2dd] overflow-hidden">
                  {item.badge && (
                    <div className="absolute top-1 right-1 z-10 bg-[#9a442a] text-white px-1.5 py-0.5 text-[8px] md:text-[10px] font-bold tracking-wide">
                      {item.badge}
                    </div>
                  )}
                  <img
                    src={item.imageUrl}
                    alt={item.title}
                    className="w-full aspect-[3/4] object-cover group-hover:scale-[1.02] transition-transform duration-300"
                  />
                  <div className="hidden md:flex absolute bottom-2 left-2.5 right-2.5 flex-wrap gap-1 text-[10px] text-[#43474c] font-mono">
                    {item.tags.map(t => (
                      <span
                        key={t}
                        onClick={(e) => { e.stopPropagation(); setActiveTag(t); }}
                        className="hover:text-[#162839] hover:underline"
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Load More Button */}
        {hasMore && (
          <div className="flex justify-center mt-12 pb-12">
            <button
              onClick={handleLoadMore}
              disabled={isLoadingMore}
              className="w-full max-w-xs border border-[#162839]/40 text-[#162839] hover:bg-[#162839] hover:text-white transition-all py-3 px-8 rounded text-xs font-semibold uppercase tracking-widest flex items-center justify-center gap-2 shadow-sm"
            >
              {isLoadingMore ? (
                <>
                  <span className="material-symbols-outlined animate-spin text-sm">progress_activity</span>
                  正在加载一屏画报...
                </>
              ) : (
                <>
                  <span className="material-symbols-outlined text-sm">expand_more</span>
                  加载更多灵感画报
                </>
              )}
            </button>
          </div>
        )}
      </main>

      {/* Lightbox Modal */}
      {previewItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-[#fbf9f4] p-4 max-w-md w-full border border-[#162839] relative">
            <img
              onClick={() => setPreviewItem(null)}
              src={previewItem.imageUrl}
              alt={previewItem.title}
              className="w-full h-auto max-h-[70vh] object-contain mb-4 cursor-zoom-out"
            />
            <h3 className="font-serif-display text-lg text-[#162839] font-bold">{previewItem.title}</h3>
            <div className="flex gap-2 mt-2 mb-6">
              {previewItem.tags.map(t => (
                <span key={t} className="text-xs bg-[#eae8e3] text-[#162839] px-2 py-0.5">{t}</span>
              ))}
            </div>
            <button
              onClick={() => setPreviewItem(null)}
              className="w-full bg-[#162839] text-white py-2 text-xs font-semibold uppercase tracking-widest"
            >
              关闭预览
            </button>
          </div>
        </div>
      )}

      {/* BottomNavBar */}
      <BottomNav currentScreen="archive" onNavigate={onNavigate} />
    </div>
  );
};
