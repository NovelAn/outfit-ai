import React, { useEffect, useState } from 'react';
import { ScreenId, GeneratedLook, InspirationItem } from '../types';
import { api, waitForReady } from '../lib/api.mjs';
import { BottomNav } from './BottomNav';
import { SideDrawer } from './SideDrawer';

interface ScreenInspirationProps {
  onNavigate: (screen: ScreenId) => void;
}

export const ScreenInspiration: React.FC<ScreenInspirationProps> = ({ onNavigate }) => {
  const [season, setSeason] = useState('秋');
  const [occasion, setOccasion] = useState('咖啡馆阅读');
  const [isGenerating, setIsGenerating] = useState(false);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [looks, setLooks] = useState<GeneratedLook[]>([]);
  const [references, setReferences] = useState<InspirationItem[]>([]);
  const [styleKeywords, setStyleKeywords] = useState<string[]>([]);
  const [toast, setToast] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  };

  const loadReferences = async () => {
    const [loadedReferences, profile] = await Promise.all([api.references(), api.profile()]);
    setReferences(loadedReferences);
    setStyleKeywords(profile.style_keywords || []);
  };

  useEffect(() => {
    loadReferences().catch((error: unknown) => {
      showToast(error instanceof Error ? error.message : '长期灵感库加载失败');
    });
  }, []);

  const handleGenerate = async () => {
    setIsGenerating(true);
    setLooks([]);
    try {
      const result = await api.generateInspiration({
        season,
        scene: occasion,
        referenceIds: references.filter((item: any) => item.status === 'ready').slice(0, 6).map((item) => item.id),
      });
      setLooks(result.looks);
      showToast(result.status === 'partial' ? `已生成 ${result.generatedCount} 张，部分图片失败，可再次生成` : '已由 AI 为您生成专属穿搭画报！');
    } catch (error) {
      showToast(error instanceof Error ? error.message : '生成失败');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleUploadInspiration = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.multiple = true;
    input.onchange = async () => {
      const files = Array.from(input.files || []);
      if (files.length === 0) return;
      showToast(`正在分析 ${files.length} 张图片并沉淀 Style DNA…`);
      const results = await Promise.allSettled(
        files.map(async (file) => {
          const uploaded = await api.uploadReference(file);
          return waitForReady(() => api.referenceStatus(uploaded.id));
        }),
      );
      const succeeded = results.filter((result) => result.status === 'fulfilled').length;
      const failed = files.length - succeeded;
      if (succeeded > 0) {
        await loadReferences();
      }
      showToast(
        failed === 0
          ? `${succeeded} 张图片已成功添加至长期灵感库！`
          : `已添加 ${succeeded} 张，${failed} 张上传或分析失败`,
      );
    };
    input.click();
  };

  return (
    <div className="bg-[#fbf9f4] text-[#1b1c19] min-h-screen pb-32">
      {/* Side Drawer Menu */}
      <SideDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        currentScreen="inspiration"
        onNavigate={onNavigate}
      />

      {/* TopAppBar */}
      <header className="fixed top-0 left-1/2 -translate-x-1/2 w-full max-w-lg z-50 bg-[#fbf9f4] flex justify-between items-center px-6 h-20 border-b border-[#e4e2dd]/40">
        <button
          onClick={() => setIsDrawerOpen(true)}
          className="text-[#162839] hover:opacity-70 transition-opacity p-1 rounded hover:bg-[#f0eee9]"
          title="打开侧边导航"
        >
          <span className="material-symbols-outlined text-[24px]">menu</span>
        </button>
        <h1 className="font-serif-display text-xl text-[#162839] font-bold">
          Outfit-AI
        </h1>
        <button className="text-[#162839] hover:opacity-70 transition-opacity">
          <span className="material-symbols-outlined text-[24px]">shopping_bag</span>
        </button>
      </header>

      {/* Main Container */}
      <main className="pt-24 max-w-lg mx-auto px-6 bg-[#fbf9f4]">
        {/* Header Section */}
        <section className="mb-10 text-left relative border-b border-[#c4c6cd]/30 pb-6">
          <div className="flex justify-between items-end mb-3">
            <h2 className="font-serif-display text-2xl md:text-3xl text-[#162839] whitespace-nowrap">
              长期灵感库
            </h2>
            {/* XPath match target: //a[.//span[contains(text(), '查看全部')]] */}
            <a
              href="#"
              onClick={(e) => { e.preventDefault(); onNavigate('archive'); }}
              className="flex items-center gap-1 text-[#43474c] hover:text-[#162839] transition-colors font-semibold uppercase tracking-widest text-xs pb-1"
            >
              <span>查看全部</span>
              <span className="material-symbols-outlined text-[18px]">arrow_forward</span>
            </a>
          </div>
          <p className="text-sm text-[#43474c]">这些心仪的瞬间，正在让 AI 越来越懂你</p>
        </section>

        {/* Long-term Reference Film Strip */}
        <section className="mb-10 -mx-6 md:mx-0">
          <div className="flex overflow-x-auto hide-scrollbar gap-6 px-6 md:px-0 pb-4">
            <div
              onClick={handleUploadInspiration}
              className="flex-none w-48 md:w-64 aspect-[3/4] border-2 border-dashed border-[#c4c6cd] flex flex-col items-center justify-center text-[#43474c] hover:border-[#162839] transition-colors cursor-pointer bg-[#f5f3ee]"
            >
              <span className="material-symbols-outlined text-[32px] mb-2">add_photo_alternate</span>
              <span className="text-xs font-semibold uppercase tracking-wider">上传灵感</span>
            </div>

            {references.slice(0, 2).map((item, index) => (
              <div key={item.id} className="flex-none w-56 md:w-72 relative group cursor-pointer" onClick={() => onNavigate('archive')}>
                <div className="aspect-[3/4] bg-[#f0eee9] overflow-hidden shadow-sm">
                  <img
                    className="object-cover w-full h-full group-hover:scale-105 transition-transform duration-300"
                    src={item.imageUrl}
                    alt={item.title}
                  />
                </div>
                <p className="mt-2 text-xs italic text-[#43474c]">
                  Archive {String(index + 1).padStart(2, '0')} / {item.category}
                </p>
              </div>
            ))}
          </div>
        </section>

        {/* Style DNA Tags */}
        <section className="mb-10 py-5 border-y border-[#c4c6cd]/30">
          <h3 className="text-xs uppercase tracking-widest font-bold text-[#9a442a] mb-3">当前 STYLE DNA</h3>
          <div className="flex flex-wrap gap-2.5">
            {(styleKeywords.length ? styleKeywords : ['等待长期灵感沉淀']).slice(0, 5).map((keyword, index) => (
              <span
                key={keyword}
                className={`px-3.5 py-1.5 rounded-full text-xs font-semibold ${
                  index === 0 ? 'bg-[#162839] text-white' : 'bg-[#eae8e3] text-[#1b1c19]'
                }`}
              >
                {keyword}
              </span>
            ))}
          </div>
        </section>

        {/* AI Generator Control Panel */}
        <section className="mb-12 bg-[#f5f3ee] p-6 relative border border-[#e4e2dd]/80 rounded-sm">
          <h3 className="font-serif-display text-xl md:text-2xl italic mb-6 text-[#162839]">
            AI 穿搭灵感生成
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <label className="block text-xs font-semibold text-[#43474c] mb-2 uppercase tracking-wider">季节</label>
              <div className="flex flex-wrap gap-2">
                {['春', '夏', '秋', '冬'].map((s) => (
                  <button
                    key={s}
                    onClick={() => setSeason(s)}
                    className={`px-4 py-2 text-xs font-semibold transition-colors ${
                      season === s
                        ? 'bg-[#162839] text-white'
                        : 'border border-[#c4c6cd] text-[#162839] hover:border-[#162839]'
                    }`}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-[#43474c] mb-2 uppercase tracking-wider">场景</label>
              <select
                value={occasion}
                onChange={(e) => setOccasion(e.target.value)}
                className="w-full bg-transparent border-b border-[#c4c6cd] py-2 text-sm text-[#162839] focus:border-[#162839] outline-none rounded-none cursor-pointer"
              >
                <option value="咖啡馆阅读">咖啡馆阅读</option>
                <option value="周末漫步">周末漫步</option>
                <option value="城市通勤">城市通勤</option>
                <option value="假日露营">假日露营</option>
              </select>
            </div>

            <div className="flex items-end">
              <button
                onClick={handleGenerate}
                disabled={isGenerating}
                className="bg-[#162839] text-white px-6 py-3 w-full text-xs font-semibold uppercase tracking-widest hover:opacity-90 transition-opacity flex items-center justify-center gap-2 disabled:opacity-50"
              >
                <span className="material-symbols-outlined text-[18px]">auto_awesome</span>
                {isGenerating ? '正在生成三图画报...' : '生成灵感'}
              </button>
            </div>
          </div>
        </section>

        {/* AI Generated Result (3-Image Generation Edition) */}
        {looks.length > 0 && <section className="mb-12 relative">
          <div className="max-w-lg mx-auto">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-8">
              {looks.map((look) => (
                <div key={look.id} className="flex flex-col group">
                  <div className="aspect-[3/4] bg-[#f0eee9] overflow-hidden shadow-md mb-3 relative">
                    <img
                      alt={look.title}
                      className="object-cover w-full h-full group-hover:scale-105 transition-transform duration-500"
                      src={look.imageUrl}
                    />
                  </div>
                  <p className="font-serif-display text-sm italic font-semibold text-[#162839]">{look.title}</p>
                  <p className="text-xs text-[#43474c] mt-0.5">{look.subtitle}</p>
                </div>
              ))}
            </div>

            <div className="text-center border-t border-[#c4c6cd]/30 pt-6">
              <p className="text-xs text-[#43474c] italic mb-6">AI 灵感图 · 不代表衣橱已有单品</p>
              <div className="flex justify-center gap-10">
                <button
                  onClick={() => showToast(`已成功保存全部${looks.length}套灵感画报至您的个人档案！`)}
                  className="flex items-center gap-2 text-[#162839] hover:opacity-70 transition-opacity"
                >
                  <span className="material-symbols-outlined text-lg text-[#9a442a]">favorite</span>
                  <span className="text-xs font-semibold uppercase tracking-wider">保存全部</span>
                </button>

                <button
                  onClick={() => showToast('穿搭画报链接已复制到剪贴板！')}
                  className="flex items-center gap-2 text-[#162839] hover:opacity-70 transition-opacity"
                >
                  <span className="material-symbols-outlined text-lg">ios_share</span>
                  <span className="text-xs font-semibold uppercase tracking-wider">分享画报</span>
                </button>
              </div>
            </div>
          </div>
        </section>}
      </main>

      {/* Toast message */}
      {toast && (
        <div className="fixed top-24 left-1/2 -translate-x-1/2 z-50 bg-[#162839] text-white px-6 py-3 text-xs uppercase tracking-wider font-semibold shadow-xl border border-white/20 animate-fade-in">
          {toast}
        </div>
      )}

      {/* Unified Bottom Navigation Bar */}
      <BottomNav currentScreen="inspiration" onNavigate={onNavigate} />
    </div>
  );
};
