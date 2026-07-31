import React, { useState, useEffect } from 'react';
import { ScreenId } from '../types';

interface SideDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  currentScreen: ScreenId;
  onNavigate: (screen: ScreenId) => void;
  locationLabel?: string;
}

const CITIES = [
  '东京', '上海', '北京', '巴黎', '纽约'
];

export const SideDrawer: React.FC<SideDrawerProps> = ({
  isOpen,
  onClose,
  currentScreen,
  onNavigate,
  locationLabel,
}) => {
  const [selectedCity, setSelectedCity] = useState('');
  const [favoritesCount, setFavoritesCount] = useState(0);
  const [ratingsCount, setRatingsCount] = useState(0);

  useEffect(() => {
    try {
      const city = localStorage.getItem('OUTFIT_AI_CITY');
      if (city) setSelectedCity(city);

      const favs = localStorage.getItem('OUTFIT_AI_FAVORITES');
      if (favs) {
        const parsed = JSON.parse(favs);
        setFavoritesCount(Array.isArray(parsed) ? parsed.length : 0);
      }

      const ratings = localStorage.getItem('OUTFIT_AI_LOOK_RATINGS');
      if (ratings) {
        const parsed = JSON.parse(ratings);
        setRatingsCount(Object.keys(parsed).length);
      }
    } catch (e) {
      console.error(e);
    }
  }, [isOpen]);

  const handleCityChange = (cityName: string) => {
    setSelectedCity(cityName);
    try {
      localStorage.setItem('OUTFIT_AI_CITY', cityName);
      // Dispatch storage event so ScreenToday updates immediately
      window.dispatchEvent(new Event('storage'));
    } catch (e) {
      console.error(e);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex animate-fade-in">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 backdrop-blur-xs transition-opacity"
        onClick={onClose}
      />

      {/* Drawer Panel */}
      <div className="relative w-80 max-w-[85vw] bg-[#fbf9f4] text-[#162839] h-full shadow-2xl flex flex-col justify-between p-6 z-10 border-r border-[#162839]/20 overflow-y-auto">
        <div>
          {/* Header & Close */}
          <div className="flex justify-between items-center mb-6 pb-4 border-b border-[#c4c6cd]/40">
            <div>
              <h2 className="font-serif-display text-xl font-bold tracking-tight">Outfit-AI</h2>
              <p className="text-[10px] text-[#9a442a] font-mono tracking-widest uppercase mt-0.5">
                Editorial & Taste AI
              </p>
            </div>
            <button
              onClick={onClose}
              className="p-1 rounded-full text-[#74777d] hover:text-[#162839] hover:bg-[#f0eee9] transition-colors"
            >
              <span className="material-symbols-outlined text-xl">close</span>
            </button>
          </div>

          {/* User Profile Summary */}
          <div className="bg-[#f0eee9] p-3.5 rounded-lg border border-[#c4c6cd]/30 mb-6 flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-[#162839] text-[#fbf9f4] flex items-center justify-center font-bold text-sm shadow-xs">
              N
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="text-xs font-bold truncate">Novelan</h3>
              <p className="text-[10px] text-[#43474c] truncate">日杂通勤风 · 基因训练中</p>
            </div>
          </div>

          {/* Location & Weather Selector */}
          <div className="mb-6">
            <label className="block text-[10px] uppercase font-bold tracking-wider text-[#74777d] mb-2">
              📍 定位与城市 / Location & City
            </label>
            <p className="text-[10px] text-[#43474c] mb-2">{locationLabel || `手动城市：${selectedCity || '未设置'}`}</p>
            <p className="text-[10px] text-[#74777d] mb-2">手动城市仅在定位不可用时使用</p>
            <div className="grid grid-cols-2 gap-1.5">
              {CITIES.map((city) => (
                <button
                  key={city}
                  onClick={() => handleCityChange(city)}
                  className={`text-[11px] p-2 rounded text-left transition-all border flex flex-col justify-between ${
                    selectedCity === city
                      ? 'bg-[#162839] text-white border-[#162839] shadow-xs'
                      : 'bg-white text-[#43474c] border-[#c4c6cd]/40 hover:border-[#162839]'
                  }`}
                >
                  <span className="font-bold text-[10px]">{city}</span>
                </button>
              ))}
            </div>
            <a
              href="https://www.openstreetmap.org/copyright"
              target="_blank"
              rel="noreferrer"
              className="block mt-2 text-[9px] text-[#74777d] underline"
            >
              © OpenStreetMap contributors
            </a>
          </div>

          {/* Main Navigation Links */}
          <div className="space-y-1 mb-6">
            <label className="block text-[10px] uppercase font-bold tracking-wider text-[#74777d] mb-2">
              🧭 页面导航 / Navigation
            </label>

            <button
              onClick={() => { onNavigate('today'); onClose(); }}
              className={`w-full flex items-center justify-between p-3 rounded text-xs font-semibold transition-colors ${
                currentScreen === 'today'
                  ? 'bg-[#9a442a] text-white'
                  : 'hover:bg-[#f0eee9] text-[#162839]'
              }`}
            >
              <div className="flex items-center gap-2.5">
                <span className="material-symbols-outlined text-lg">auto_stories</span>
                <span>今日 Look 推荐</span>
              </div>
              <span className="material-symbols-outlined text-sm opacity-60">chevron_right</span>
            </button>

            <button
              onClick={() => { onNavigate('wardrobe'); onClose(); }}
              className={`w-full flex items-center justify-between p-3 rounded text-xs font-semibold transition-colors ${
                currentScreen === 'wardrobe'
                  ? 'bg-[#9a442a] text-white'
                  : 'hover:bg-[#f0eee9] text-[#162839]'
              }`}
            >
              <div className="flex items-center gap-2.5">
                <span className="material-symbols-outlined text-lg">grid_view</span>
                <span>我的数字化衣橱</span>
              </div>
              <span className="material-symbols-outlined text-sm opacity-60">chevron_right</span>
            </button>

            <button
              onClick={() => { onNavigate('inspiration'); onClose(); }}
              className={`w-full flex items-center justify-between p-3 rounded text-xs font-semibold transition-colors ${
                currentScreen === 'inspiration'
                  ? 'bg-[#9a442a] text-white'
                  : 'hover:bg-[#f0eee9] text-[#162839]'
              }`}
            >
              <div className="flex items-center gap-2.5">
                <span className="material-symbols-outlined text-lg">autoplay</span>
                <span>AI 灵感生成</span>
              </div>
              <span className="material-symbols-outlined text-sm opacity-60">chevron_right</span>
            </button>

            <button
              onClick={() => { onNavigate('archive'); onClose(); }}
              className={`w-full flex items-center justify-between p-3 rounded text-xs font-semibold transition-colors ${
                currentScreen === 'archive'
                  ? 'bg-[#9a442a] text-white'
                  : 'hover:bg-[#f0eee9] text-[#162839]'
              }`}
            >
              <div className="flex items-center gap-2.5">
                <span className="material-symbols-outlined text-lg">auto_awesome</span>
                <span>灵感画报存档</span>
              </div>
              <span className="material-symbols-outlined text-sm opacity-60">chevron_right</span>
            </button>

            <button
              onClick={() => { onNavigate('profile'); onClose(); }}
              className={`w-full flex items-center justify-between p-3 rounded text-xs font-semibold transition-colors ${
                currentScreen === 'profile'
                  ? 'bg-[#9a442a] text-white'
                  : 'hover:bg-[#f0eee9] text-[#162839]'
              }`}
            >
              <div className="flex items-center gap-2.5">
                <span className="material-symbols-outlined text-lg">person</span>
                <span>个人 DNA & 品味档案</span>
              </div>
              <span className="material-symbols-outlined text-sm opacity-60">chevron_right</span>
            </button>
          </div>

          {/* AI Taste Status Widget */}
          <div className="bg-[#162839] text-white p-4 rounded-lg shadow-md mb-6">
            <div className="flex justify-between items-center mb-2">
              <span className="text-[10px] font-mono text-[#f4dfcb] uppercase tracking-wider font-bold">
                AI Engine Active
              </span>
              <span className="text-xs font-bold text-[#f4dfcb]">
                {Math.min(98, 85 + ratingsCount * 4)}% Match
              </span>
            </div>
            <p className="text-[11px] text-[#c4c6cd] leading-tight mb-2">
              基于 {ratingsCount} 次真实反馈评价 & 衣橱基因深度训练
            </p>
            <div className="flex items-center gap-2 text-[10px] text-[#f4dfcb] pt-2 border-t border-white/10 font-mono">
              <span>❤️ 已收藏: {favoritesCount} 套</span>
              <span>·</span>
              <span>反馈学习: {ratingsCount} 次</span>
            </div>
          </div>
        </div>

        {/* Footer info */}
        <div className="pt-4 border-t border-[#c4c6cd]/30 text-center">
          <p className="text-[10px] text-[#74777d] font-mono">Outfit-AI v2.4 · Japanese Fashion Tech</p>
        </div>
      </div>
    </div>
  );
};
