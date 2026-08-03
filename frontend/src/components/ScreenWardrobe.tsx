import React, { useEffect, useRef, useState } from 'react';
import { ScreenId, OutfitItem } from '../types';
import { api, categoryCode, createSingleFlight, mapWardrobeItem, settleInPairs, waitForReady } from '../lib/api.mjs';
import { BottomNav } from './BottomNav';
import { SideDrawer } from './SideDrawer';

interface ScreenWardrobeProps {
  onNavigate: (screen: ScreenId) => void;
}

const INITIAL_ITEMS: OutfitItem[] = [
  {
    id: '1',
    brand: 'J.CREW',
    name: '青年布衬衫',
    category: '上装',
    imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuB6njvbZZTTniX4WiGF6i67KzJy1LjhgnC_FcBPWFRpgCf_mBKCXkNKxv1MXdqke2dMCyuau1S1YLjMLf8Z6i6FvAhBg65K_FzVpO0-HfHtQiaytM8U7UnBaCHgQenrtcWjjtVEQ_tIMAuQi7bnI7lMCO9EIll2EoXALvCULPHw8rdQCmkhBHgbkkfTxKNeAhjWQrkHSDI9PieZuXxqHv1QwWrzCzSX0YLkZalzuFKU6HqDGOf5tNNT34V97qeZkTT4oQ'
  },
  {
    id: '2',
    brand: 'PATAGONIA',
    name: '亚麻短裤',
    category: '下装',
    imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuB20veJH_yX5gI_OSZevdRlACCjvGM2dEMrY4Dl09x-m-Ua8uwMRhgnLLO5_-KO1uFdhw_hnwOhPj-KHqvvCqrU48laVBo5NwF9JnzQ6eGO9lw_JSrF2L54ju3Pyw4wnZAIwJ9Eg0JSpsnxK9fLWCZhRBUCKhQUaSKCcT5scFwS0XmZEZfWm5UEnJXFC4wGWEbyEeHgo8Fola4cl42iCD4Uo0WhC83DitT39P21pbBTlv2qsZNaiYfvoJu001dj4kRCvg'
  },
  {
    id: '3',
    brand: 'JORDAN',
    name: 'AJ1 低帮摩卡',
    category: '鞋履',
    imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuDcbM69daMxV2kEDSh9KtN3jPJcVcn6XgnLh23TD-MiLSqSBsPYRkyyU_Kzht-la5YYcXeMU4thYIS3qT0JMspbtbY8sISow7xCYPy3LzhdHb9sTqOAzkyNxBYCpm5b-Uc9b2Wub7GcEuKyx_0pPY_3TMQumm9K6sKcjAK8sls3Fn_OgSVqZ6ajtb8tAq7hfJFyx5157377xXOZYUmBuuEmsIJT11lMPpapPj0cLMmwleoA2qC1bqIa__SJ3WGRjeks9g'
  },
  {
    id: '4',
    brand: 'AURALEE',
    name: '棉质风衣',
    category: '上装',
    imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBuRUKU2ptL8Ug55H8Zc8CuPihQ7OQ9rzIVjv1mcpJmtdT7v9dYNc1xgKxavZl-rFOCr8waLbcjC1bxY-pe3IUW3z8Y6z5wlvPRhqPpqDAo3RQWG50r3gk-FrQx4bq4vqL8zNQznl1UbMPiPAox_3ToAiKWnKld1RtRcgJaG-TF35WHoYESsnP0ra_F6NxujGy8Ca-qcRZhWWc022XrzI2znI_UdaRbkFnCP5ZJJ1GnbFjS9xlPApFw'
  },
  {
    id: '5',
    brand: 'BEAMS PLUS',
    name: '重磅口袋白T',
    category: '上装',
    imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuDFEJapTzg7M2pWwwrAPXMMImbFzrYpkWckOASqNeyP-hx0RuVCZMR_hOAczTSsxi88EKn-yAhj3v12qBClhH3X2JUBtmX-3No4Q3tHG7M_qgxJU3BpZ9Z7ux-iGduVDAShKM_VfHmG1WLA5irrPRU_a5ZMddYMH0sZvcH_Y93s-JrfJ-IU6IenJUxj29G4AEK2wyyihIgAnNwgsCmoYkHhoyU3q7kvlRPI7CA1as9nTSGeCo8728tJ'
  },
  {
    id: '6',
    brand: 'COMOLI',
    name: '海军蓝阔腿卡其裤',
    category: '下装',
    imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuAPNznerXhWs_PBUIjy3_5VGM9WlIxCkDTAU0iMqDgtdZej0uNDXIWLdKBvxcJgxLc2IsrtDgnYxWrMvf1Fr_ZFBHxCIzJHEnDVMa8qkZlKkzdPZrTGYECrSnYw0-Q9jfu1OGlWfAZyZPc_m32DFLTZnpFwa02TamNqOy3Qb87tIJ1m8NT-Hh47d3ri26OPD_OmaqmpSt7jub6jiJ94eisU4gnGwxQbEI6eSo0jTAFU0VA6YU6KjHHB'
  }
];

const MORE_ITEMS: OutfitItem[] = [
  {
    id: '7',
    brand: 'MARNI',
    name: '马海毛撞色开衫',
    category: '上装',
    imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBHql_kA1QBu5PdlksjBh57JEYklOBf9QFgGOemLmBKOIcR1_4HYVUfx8__czG7X8xJao48bfq_5Qc9WiKU7vs8zlNs-5QTgdbLuw6s9pkespNnL89bpuEqBv-xyt6lMXV_U6_NyBkZqqFnkkTXwTDK9DdoWOFQS44o0UhL4iNLmv93AlS7xo_xDcT7UbE4-2cbn-uYJ4tOAtGTt3goA9h1iucCnjRKzMK3bdeVtB88eXkop0hCgDRg',
    isNew: true
  },
  {
    id: '8',
    brand: 'STUDIO NICHOLSON',
    name: '双褶极简休闲裤',
    category: '下装',
    imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuC18NBg_KXnEdXRsQepIDSSJb9GeIizAGMZ8XSKWTrMGrGc0HCBP3RHeOpjumEg3nR9SjOro5VFO_EA4P7t0ETN8M8Xkzc3ZzEZ2vz7xH4ciBGiC_sD-IKvmdoYyVXuWTT3vAWLlif323FrjbbdGdBpwk0QA8DV1A5M5I2jqRB8IeBZr1j558k_MEw8DzrHbY8b9soPOUmeOpjumEg3nR9SjOro5VFO_EA4P7t0ETN8M8Xkzc3ZzEZ2vz7xH4ciBGiC_sD-IKvmdoYyVXuWTT3vAWLlif323FrjbbdGdBpwk0QA8DV1A5M5I2jqRB8IeBZr1j558k_MEw8DzrHbY8b9soPOUmeObmYAU0B7KTVaKAlRXjSmhFLwWz79R3lgUubwsp1nvbk',
    isNew: true
  },
  {
    id: '9',
    brand: 'KAPITAL',
    name: '刺绣水洗牛仔外套',
    category: '上装',
    imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBuRUKU2ptL8Ug55H8Zc8CuPihQ7OQ9rzIVjv1mcpJmtdT7v9dYNc1xgKxavZl-rFOCr8waLbcjC1bxY-pe3IUW3z8Y6z5wlvPRhqPpqDAo3RQWG50r3gk-FrQx4bq4vqL8zNQznl1UbMPiPAox_3ToAiKWnKld1RtRcgJaG-TF35WHoYESsnP0ra_F6NxujGy8Ca-qcRZhWWc022XrzI2znI_UdaRbkFnCP5ZJJ1GnbFjS9xlPApFw'
  },
  {
    id: '10',
    brand: 'LEMAIRE',
    name: '麂皮复古鞋履',
    category: '鞋履',
    imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuAN-vdwTEbVAujzyoBX7uIMHV9bkCM_LXhzfKJcXTYcfLA5h7rIDCmaV6Pj98BAaCjURMJR-fgUe3chDKgbCCbWQzw5ElvQS2MwBej4bX2ZkNNyeD8xji_miQIM1jzaMTpRxHiCbKoTe9V524eAGMU1I7ddUgdDbkATGdQFuNS7oLHEITmf289th8ZJkbDCU_tibwfu9ft0F5vCqk9D6LtJsP2tVyp4p9Ae1c4bzyVqlSLRLmAJZQXr'
  }
];

interface WardrobeEditDraft {
  name: string;
  category: OutfitItem['category'];
  primaryColor: string;
  secondaryColor: string;
  material: string;
  thickness: string;
  fit: string;
  styles: string;
  tags: string;
  seasons: string;
  occasions: string;
}

const THICKNESS_TAGS = ['轻薄', '适中', '厚实'];

const labelsFromText = (value: string) => value
  .split(/[、,，]/)
  .map((label) => label.trim())
  .filter(Boolean);

const editDraftFromItem = (item: OutfitItem): WardrobeEditDraft => ({
  name: item.name,
  category: item.category,
  primaryColor: item.primaryColor || '',
  secondaryColor: item.secondaryColor || '',
  material: item.material || '',
  thickness: item.thickness || '',
  fit: item.fit || '',
  styles: (item.styles || []).join('、'),
  tags: (item.tags || []).filter((tag) => !THICKNESS_TAGS.includes(tag)).join('、'),
  seasons: (item.seasons || []).join('、'),
  occasions: (item.occasions || []).join('、'),
});

const payloadFromDraft = (draft: WardrobeEditDraft) => ({
  name: draft.name.trim(),
  category: categoryCode(draft.category),
  primary_color: draft.primaryColor.trim(),
  secondary_color: draft.secondaryColor.trim(),
  material: draft.material.trim(),
  fit: draft.fit.trim(),
  styles: labelsFromText(draft.styles),
  tags: [
    ...labelsFromText(draft.tags).filter((tag) => !THICKNESS_TAGS.includes(tag)),
    ...(THICKNESS_TAGS.includes(draft.thickness) ? [draft.thickness] : []),
  ].filter((tag, index, values) => values.indexOf(tag) === index),
  seasons: labelsFromText(draft.seasons),
  occasions: labelsFromText(draft.occasions),
  confirmed_by_user: true,
});

export const ScreenWardrobe: React.FC<ScreenWardrobeProps> = ({ onNavigate }) => {
  const [selectedCategory, setSelectedCategory] = useState<string>('全部');
  const [items, setItems] = useState<OutfitItem[]>([]);
  const [selectedItem, setSelectedItem] = useState<OutfitItem | null>(null);
  const [editDraft, setEditDraft] = useState<WardrobeEditDraft | null>(null);
  const [isEditingItem, setIsEditingItem] = useState<boolean>(false);
  const [isDeleteConfirming, setIsDeleteConfirming] = useState<boolean>(false);
  const [isMutatingItem, setIsMutatingItem] = useState<boolean>(false);
  const [isAdding, setIsAdding] = useState<boolean>(false);
  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(false);
  const [newBrand, setNewBrand] = useState('');
  const [newName, setNewName] = useState('');
  const [newCategory, setNewCategory] = useState<OutfitItem['category']>('上装');
  const [newItemImageUrl, setNewItemImageUrl] = useState<string>('');
  const [newItemFile, setNewItemFile] = useState<File | null>(null);
  const singleFileInputRef = useRef<HTMLInputElement | null>(null);
  const batchFlightRef = useRef(createSingleFlight());

  // Batch import and AI extraction state
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [isExtracting, setIsExtracting] = useState<boolean>(false);
  const [extractCount, setExtractCount] = useState<number>(0);
  const [hasMore, setHasMore] = useState<boolean>(false);
  const [isLoadingMore, setIsLoadingMore] = useState<boolean>(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const categories = ['全部', '上装', '下装', '鞋履', '配饰'];

  const filteredItems = selectedCategory === '全部'
    ? items
    : items.filter(item => item.category === selectedCategory);

  const triggerToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  const loadItems = async () => {
    try {
      setItems(await api.wardrobe());
    } catch (error) {
      triggerToast(error instanceof Error ? error.message : '衣橱加载失败');
    }
  };

  useEffect(() => {
    void loadItems();
  }, []);

  const handleBatchImportClick = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  const handleFilesSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;

    await batchFlightRef.current(async () => {
      const count = files.length;
      setExtractCount(count);
      setIsExtracting(true);

      try {
        const results = await settleInPairs(
          files,
          async (file) => {
            const uploaded = await api.uploadWardrobe(file);
            const ready = await waitForReady(() => api.wardrobeStatus(uploaded.id));
            await api.confirmWardrobe(uploaded.id, {
              ...(ready.attributes || {}),
              confirmed_by_user: true,
            });
          },
        );
        setItems(await api.wardrobe());
        const succeeded = results.filter(({ status }) => status === 'fulfilled').length;
        triggerToast(`批量处理完成：成功 ${succeeded} 张，失败 ${count - succeeded} 张`);
      } catch (error) {
        triggerToast(error instanceof Error ? error.message : '衣橱刷新失败');
      } finally {
        setIsExtracting(false);
        if (fileInputRef.current) fileInputRef.current.value = '';
      }
    });
  };

  const handleLoadMore = () => {
    setIsLoadingMore(true);
    setTimeout(() => {
      setItems(prev => [...prev, ...MORE_ITEMS]);
      setHasMore(false);
      setIsLoadingMore(false);
      triggerToast('已加载更多衣橱藏品');
    }, 600);
  };

  const handleSingleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const url = URL.createObjectURL(file);
      setNewItemFile(file);
      setNewItemImageUrl(url);
    }
  };

  const handleAddItem = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newBrand || !newName || !newItemFile) {
      triggerToast('请选择真实衣物照片并填写品牌与名称');
      return;
    }
    setIsExtracting(true);
    setExtractCount(1);
    try {
      const uploaded = await api.uploadWardrobe(newItemFile);
      const ready = await waitForReady(() => api.wardrobeStatus(uploaded.id));
      const confirmed = await api.confirmWardrobe(uploaded.id, {
        ...(ready.attributes || {}),
        brand: newBrand.toUpperCase(),
        name: newName,
        category: categoryCode(newCategory),
        confirmed_by_user: true,
      });
      setItems((current) => [
        { ...mapWardrobeItem(confirmed), isNew: true } as OutfitItem,
        ...current,
      ]);
      setNewBrand('');
      setNewName('');
      setNewItemFile(null);
      setNewItemImageUrl('');
      setIsAdding(false);
      triggerToast('单品已去背景、识别并录入衣橱');
    } catch (error) {
      triggerToast(error instanceof Error ? error.message : '单品录入失败');
    } finally {
      setIsExtracting(false);
    }
  };

  const handleEditItem = () => {
    if (!selectedItem) return;
    setEditDraft(editDraftFromItem(selectedItem));
    setIsEditingItem(true);
    setIsDeleteConfirming(false);
  };

  const handleSaveItem = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedItem || !editDraft) return;
    setIsMutatingItem(true);
    try {
      const updated = await api.updateWardrobe(
        selectedItem.id,
        payloadFromDraft(editDraft),
      );
      const mapped = mapWardrobeItem(updated) as OutfitItem;
      setItems((current) => current.map((item) => (item.id === mapped.id ? mapped : item)));
      setSelectedItem(mapped);
      setIsEditingItem(false);
      setEditDraft(null);
      triggerToast('单品信息已更新');
    } catch (error) {
      triggerToast(error instanceof Error ? error.message : '单品信息保存失败');
    } finally {
      setIsMutatingItem(false);
    }
  };

  const handleDeleteItem = async () => {
    if (!selectedItem) return;
    setIsMutatingItem(true);
    try {
      await api.deleteWardrobe(selectedItem.id);
      setItems((current) => current.filter((item) => item.id !== selectedItem.id));
      setSelectedItem(null);
      setEditDraft(null);
      setIsEditingItem(false);
      setIsDeleteConfirming(false);
      triggerToast('单品及图片已删除');
    } catch (error) {
      triggerToast(error instanceof Error ? error.message : '单品删除失败');
    } finally {
      setIsMutatingItem(false);
    }
  };

  return (
    <div className="bg-[#fbf9f4] text-[#1b1c19] min-h-screen pb-32">
      {/* Hidden File Input for Batch Wardrobe Import */}
      <input
        type="file"
        ref={fileInputRef}
        multiple
        accept="image/*"
        onChange={handleFilesSelected}
        className="hidden"
      />

      {/* Hidden File Input for Single Item Modal Upload */}
      <input
        type="file"
        ref={singleFileInputRef}
        accept="image/*"
        onChange={handleSingleFileChange}
        className="hidden"
      />

      {/* Side Drawer Menu */}
      <SideDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        currentScreen="wardrobe"
        onNavigate={onNavigate}
      />

      {/* TopAppBar */}
      <header className="fixed top-0 w-full z-50 bg-[#fbf9f4]/95 backdrop-blur-md flex justify-between items-center px-6 h-16 border-b border-[#e4e2dd]/60 max-w-lg left-1/2 -translate-x-1/2">
        <button
          onClick={() => setIsDrawerOpen(true)}
          className="text-[#162839] hover:opacity-70 transition-opacity p-1 rounded hover:bg-[#f0eee9]"
          title="打开侧边导航"
        >
          <span className="material-symbols-outlined text-[22px]">menu</span>
        </button>
        <h1 className="font-serif-display text-lg text-[#162839] font-bold">
          Outfit-AI
        </h1>
        <div className="flex items-center gap-3">
          <button
            onClick={handleBatchImportClick}
            disabled={isExtracting}
            className="text-[#9a442a] hover:opacity-80 disabled:opacity-40 disabled:cursor-not-allowed transition-opacity flex items-center gap-1 text-xs font-semibold bg-[#f4dfcb]/30 px-2.5 py-1 rounded border border-[#9a442a]/20"
            title="批量导入真实衣橱"
          >
            <span className="material-symbols-outlined text-[16px]">cloud_upload</span>
            <span className="hidden sm:inline">批量导入</span>
          </button>
          <button
            onClick={() => setIsAdding(true)}
            className="text-[#162839] hover:opacity-70 transition-opacity flex items-center"
            title="添加单品"
          >
            <span className="material-symbols-outlined text-[22px]">add_circle</span>
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="pt-20 px-6 flex flex-col gap-5 max-w-lg mx-auto">
        {/* Toast Notification */}
        {toastMessage && (
          <div className="fixed top-20 left-1/2 -translate-x-1/2 z-50 bg-[#162839] text-white px-5 py-2.5 rounded shadow-xl text-xs font-medium border border-white/20 animate-fade-in flex items-center gap-2">
            <span className="material-symbols-outlined text-[#f4dfcb] text-base">check_circle</span>
            {toastMessage}
          </div>
        )}

        {/* AI Processing Status Banner (Appears ONLY AFTER image upload action) */}
        {isExtracting && (
          <div className="bg-[#162839] text-white p-4 rounded-lg shadow-md flex items-center gap-3 animate-pulse border border-[#9a442a]/40">
            <span className="material-symbols-outlined text-[#f4dfcb] animate-spin">auto_awesome</span>
            <div className="flex-1">
              <div className="flex justify-between items-center mb-1">
                <h3 className="text-xs font-bold text-[#f4dfcb] uppercase tracking-wider">
                  AI 智能特征提取中
                </h3>
                <span className="text-[10px] bg-[#9a442a] text-white px-1.5 py-0.5 rounded font-mono">
                  处理中
                </span>
              </div>
              <p className="text-[11px] text-gray-200">
                正在识别 {extractCount} 张上传实拍照片的材质、材质落色与裁剪分类...
              </p>
              <p className="text-[10px] text-gray-300 mt-1">
                首次处理需要准备本地去背景模型，可能耗时 2–3 分钟；缓存后会明显加快。
              </p>
              <div className="w-full bg-white/20 h-1 rounded-full mt-2 overflow-hidden">
                <div className="bg-[#f4dfcb] h-full w-2/3 animate-pulse"></div>
              </div>
            </div>
          </div>
        )}

        {/* Header Section */}
        <section className="flex flex-col gap-1.5 relative pt-2">
          <h2 className="font-serif-display text-2xl text-[#162839] font-semibold">我的衣橱</h2>
          <div className="flex justify-between items-center">
            <p className="text-xs text-[#4e6073] leading-relaxed">
              您的私人藏品，随时智能组合。
            </p>
            <span className="text-xs text-[#43474c] font-mono">{items.length} 件数字化单品</span>
          </div>
        </section>

        {/* Category Navigation */}
        <nav className="flex gap-5 overflow-x-auto hide-scrollbar py-2 border-b border-[#e4e2dd]">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`text-xs tracking-wider uppercase shrink-0 transition-colors relative pb-2 ${
                selectedCategory === cat
                  ? 'text-[#9a442a] font-bold after:content-[""] after:absolute after:bottom-0 after:left-0 after:w-full after:h-[2px] after:bg-[#9a442a]'
                  : 'text-[#43474c] hover:text-[#162839]'
              }`}
            >
              {cat}
            </button>
          ))}
        </nav>

        {/* Grid View */}
        <section className="grid grid-cols-3 gap-2 mt-1 pb-6">
          {filteredItems.map((item) => (
            <article
              key={item.id}
              onClick={() => setSelectedItem(item)}
              className="flex flex-col items-center gap-1 group cursor-pointer bg-white/60 p-1.5 rounded-md border border-[#e4e2dd]/60 hover:shadow-sm transition-all"
            >
              <div className="w-full aspect-[4/5] flex items-center justify-center relative overflow-hidden rounded bg-white/40">
                <img
                  alt={item.name}
                  className="object-contain w-full h-full group-hover:scale-105 transition-transform duration-300"
                  src={item.imageUrl}
                />
                {item.isNew && (
                  <span className="absolute top-1 right-1 bg-[#9a442a] text-white text-[9px] px-1.5 py-0.5 font-mono rounded">
                    NEW
                  </span>
                )}
              </div>
              {item.brand && (
                <span className="text-[9px] font-bold text-[#162839] text-center uppercase tracking-wide mt-0.5 line-clamp-1">
                  {item.brand}
                </span>
              )}
              <span className="text-[10px] leading-tight text-[#43474c] text-center line-clamp-2">{item.name}</span>
            </article>
          ))}
        </section>

        {/* Load More (Lazy Loading) Button */}
        {hasMore && selectedCategory === '全部' && (
          <div className="flex justify-center pt-2 pb-12">
            <button
              onClick={handleLoadMore}
              disabled={isLoadingMore}
              className="w-full max-w-xs border border-[#162839]/30 text-[#162839] hover:bg-[#162839] hover:text-white transition-all py-2.5 px-6 rounded text-xs font-semibold uppercase tracking-widest flex items-center justify-center gap-2"
            >
              {isLoadingMore ? (
                <>
                  <span className="material-symbols-outlined animate-spin text-sm">progress_activity</span>
                  正在加载藏品...
                </>
              ) : (
                <>
                  <span className="material-symbols-outlined text-sm">expand_more</span>
                  加载更多衣橱单品
                </>
              )}
            </button>
          </div>
        )}
      </main>

      {/* Item Detail Modal */}
      {selectedItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="bg-[#fbf9f4] p-6 max-w-sm w-full max-h-[90vh] overflow-y-auto rounded-lg border border-[#162839] relative shadow-2xl">
            <div className="w-full aspect-square bg-white p-4 mb-4 flex items-center justify-center rounded">
              <img src={selectedItem.imageUrl} alt={selectedItem.name} className="max-h-full object-contain" />
            </div>
            {isDeleteConfirming ? (
              <div className="space-y-4">
                <h3 className="font-serif-display text-xl text-[#162839] font-bold">确认删除单品？</h3>
                <p className="text-sm text-[#43474c] leading-relaxed">
                  将删除“{selectedItem.name}”以及原图和去背景图片，此操作无法恢复。
                </p>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setIsDeleteConfirming(false)}
                    disabled={isMutatingItem}
                    className="flex-1 border border-[#162839] text-[#162839] py-2.5 rounded text-xs font-semibold disabled:opacity-50"
                  >
                    取消删除
                  </button>
                  <button
                    type="button"
                    onClick={() => void handleDeleteItem()}
                    disabled={isMutatingItem}
                    className="flex-1 bg-[#9a442a] text-white py-2.5 rounded text-xs font-semibold disabled:opacity-50"
                  >
                    {isMutatingItem ? '删除中…' : '确认删除'}
                  </button>
                </div>
              </div>
            ) : isEditingItem && editDraft ? (
              <form onSubmit={handleSaveItem} className="space-y-3 text-xs">
                <div className="flex items-center justify-between">
                  <h3 className="font-serif-display text-xl text-[#162839] font-bold">编辑信息</h3>
                  <span className="text-[#43474c]">{selectedItem.brand || '未填写品牌'}</span>
                </div>
                <label className="block text-[#43474c] font-semibold">
                  单品名称
                  <input
                    value={editDraft.name}
                    onChange={(e) => setEditDraft({ ...editDraft, name: e.target.value })}
                    className="mt-1 w-full p-2 border border-[#c4c6cd] rounded bg-white text-[#162839]"
                    required
                  />
                </label>
                <label className="block text-[#43474c] font-semibold">
                  分类
                  <select
                    value={editDraft.category}
                    onChange={(e) => setEditDraft({ ...editDraft, category: e.target.value as OutfitItem['category'] })}
                    className="mt-1 w-full p-2 border border-[#c4c6cd] rounded bg-white text-[#162839]"
                  >
                    <option value="上装">上装</option>
                    <option value="下装">下装</option>
                    <option value="鞋履">鞋履</option>
                    <option value="配饰">配饰</option>
                  </select>
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {([
                    ['primaryColor', '主色'],
                    ['secondaryColor', '辅色'],
                    ['material', '材质'],
                    ['fit', '版型'],
                  ] as const).map(([key, label]) => (
                    <label key={key} className="block text-[#43474c] font-semibold">
                      {label}
                      <input
                        value={editDraft[key]}
                        onChange={(e) => setEditDraft({ ...editDraft, [key]: e.target.value })}
                        className="mt-1 w-full p-2 border border-[#c4c6cd] rounded bg-white text-[#162839]"
                      />
                    </label>
                  ))}
                </div>
                <label className="block text-[#43474c] font-semibold">
                  厚薄度
                  <select
                    value={editDraft.thickness}
                    onChange={(e) => setEditDraft({ ...editDraft, thickness: e.target.value })}
                    className="mt-1 w-full p-2 border border-[#c4c6cd] rounded bg-white text-[#162839]"
                  >
                    <option value="">未设置</option>
                    {THICKNESS_TAGS.map((value) => <option key={value} value={value}>{value}</option>)}
                  </select>
                </label>
                {([
                  ['styles', '风格标签'],
                  ['tags', '其他标签'],
                  ['seasons', '适用季节'],
                  ['occasions', '适用场景'],
                ] as const).map(([key, label]) => (
                  <label key={key} className="block text-[#43474c] font-semibold">
                    {label}（用顿号分隔）
                    <input
                      value={editDraft[key]}
                      onChange={(e) => setEditDraft({ ...editDraft, [key]: e.target.value })}
                      className="mt-1 w-full p-2 border border-[#c4c6cd] rounded bg-white text-[#162839]"
                    />
                  </label>
                ))}
                <div className="flex gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => { setIsEditingItem(false); setEditDraft(null); }}
                    disabled={isMutatingItem}
                    className="flex-1 border border-[#162839] text-[#162839] py-2.5 rounded text-xs font-semibold disabled:opacity-50"
                  >
                    取消
                  </button>
                  <button
                    type="submit"
                    disabled={isMutatingItem}
                    className="flex-1 bg-[#162839] text-white py-2.5 rounded text-xs font-semibold disabled:opacity-50"
                  >
                    {isMutatingItem ? '保存中…' : '保存修改'}
                  </button>
                </div>
              </form>
            ) : (
              <>
                <span className="text-xs font-mono text-[#9a442a] uppercase font-semibold">{selectedItem.category}</span>
                <h3 className="font-serif-display text-xl text-[#162839] font-bold mt-1">{selectedItem.brand || '未填写品牌'}</h3>
                <p className="text-sm text-[#43474c] mt-1 mb-5">{selectedItem.name}</p>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={handleEditItem}
                    className="flex-1 border border-[#162839] text-[#162839] py-2.5 rounded text-xs font-semibold hover:bg-[#162839]/5"
                  >
                    编辑信息
                  </button>
                  <button
                    type="button"
                    onClick={() => setIsDeleteConfirming(true)}
                    className="flex-1 border border-[#9a442a] text-[#9a442a] py-2.5 rounded text-xs font-semibold hover:bg-[#9a442a]/5"
                  >
                    删除单品
                  </button>
                </div>
                <button
                  type="button"
                  onClick={() => setSelectedItem(null)}
                  className="w-full mt-2 bg-[#162839] text-white py-2.5 rounded text-xs font-semibold uppercase tracking-widest hover:opacity-90"
                >
                  关闭
                </button>
              </>
            )}
          </div>
        </div>
      )}

      {/* Single Add Item Modal */}
      {isAdding && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <form onSubmit={handleAddItem} className="bg-[#fbf9f4] p-6 max-w-sm w-full rounded-lg border border-[#162839] relative shadow-2xl">
            <h3 className="font-serif-display text-lg text-[#162839] font-bold mb-4">手动录入新单品</h3>
            <div className="space-y-4 text-xs">
              <div>
                <label className="block text-[#43474c] uppercase font-semibold mb-1">单品图片 / Item Photo</label>
                {newItemImageUrl ? (
                  <div className="relative w-full h-32 bg-white rounded border border-[#c4c6cd] p-2 flex items-center justify-center group">
                    <img src={newItemImageUrl} alt="Preview" className="max-h-full max-w-full object-contain" />
                    <button
                      type="button"
                      onClick={() => setNewItemImageUrl('')}
                      className="absolute top-2 right-2 bg-[#ba1a1a] text-white p-1 rounded-full text-xs shadow hover:opacity-90 flex items-center justify-center"
                      title="移除图片"
                    >
                      <span className="material-symbols-outlined text-sm">close</span>
                    </button>
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={() => singleFileInputRef.current?.click()}
                    className="w-full h-24 border-2 border-dashed border-[#c4c6cd] rounded bg-white/60 hover:bg-white transition-colors flex flex-col items-center justify-center gap-1 text-[#74777d] hover:text-[#162839]"
                  >
                    <span className="material-symbols-outlined text-2xl">add_a_photo</span>
                    <span className="text-[11px] font-medium">点击选择或上传单品照片</span>
                  </button>
                )}
              </div>
              <div>
                <label className="block text-[#43474c] uppercase font-semibold mb-1">品牌 / Brand</label>
                <input
                  type="text"
                  value={newBrand}
                  onChange={(e) => setNewBrand(e.target.value)}
                  placeholder="如: UNIQLO, MARNI..."
                  className="w-full p-2 border border-[#c4c6cd] rounded bg-white text-[#162839]"
                  required
                />
              </div>
              <div>
                <label className="block text-[#43474c] uppercase font-semibold mb-1">单品名称 / Item Name</label>
                <input
                  type="text"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="如: 纯棉牛津纺衬衫..."
                  className="w-full p-2 border border-[#c4c6cd] rounded bg-white text-[#162839]"
                  required
                />
              </div>
              <div>
                <label className="block text-[#43474c] uppercase font-semibold mb-1">分类 / Category</label>
                <select
                  value={newCategory}
                  onChange={(e) => setNewCategory(e.target.value as any)}
                  className="w-full p-2 border border-[#c4c6cd] rounded bg-white text-[#162839]"
                >
                  <option value="上装">上装</option>
                  <option value="下装">下装</option>
                  <option value="鞋履">鞋履</option>
                  <option value="配饰">配饰</option>
                </select>
              </div>
            </div>
            <div className="flex gap-2 mt-6">
              <button
                type="button"
                onClick={() => setIsAdding(false)}
                className="flex-1 border border-[#162839] text-[#162839] py-2 rounded text-xs uppercase tracking-wider font-semibold"
              >
                取消
              </button>
              <button
                type="submit"
                className="flex-1 bg-[#162839] text-white py-2 rounded text-xs uppercase tracking-wider font-semibold"
              >
                保存单品
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Unified Bottom Navigation Bar */}
      <BottomNav currentScreen="wardrobe" onNavigate={onNavigate} />
    </div>
  );
};
