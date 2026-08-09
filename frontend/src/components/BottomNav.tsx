import React from 'react';
import { ScreenId } from '../types';

interface BottomNavProps {
  currentScreen: ScreenId;
  onNavigate: (screen: ScreenId) => void;
}

export const BottomNav: React.FC<BottomNavProps> = ({ currentScreen, onNavigate }) => {
  const tabs: { id: ScreenId; label: string; icon: string }[] = [
    { id: 'today', label: '今日', icon: 'auto_stories' },
    { id: 'wardrobe', label: '衣橱', icon: 'grid_view' },
    { id: 'inspiration', label: '灵感', icon: 'auto_awesome' },
    { id: 'profile', label: '我的', icon: 'person' },
  ];

  return (
    <nav aria-label="主导航" className="fixed inset-x-0 bottom-0 z-[60] bg-[#fbf9f4]/95 backdrop-blur-md border-t border-[#e4e2dd] shadow-[0_-4px_20px_rgba(0,0,0,0.03)] px-6 py-2 pb-[calc(1.5rem+env(safe-area-inset-bottom))] flex justify-around items-center max-w-lg mx-auto">
      {tabs.map((tab) => {
        const isActive = currentScreen === tab.id || (tab.id === 'inspiration' && currentScreen === 'archive');
        return (
          <button
            key={tab.id}
            type="button"
            onClick={() => onNavigate(tab.id)}
            className={`flex flex-col items-center justify-center transition-all px-3 py-1 rounded-md relative ${
              isActive
                ? 'text-[#9a442a] font-bold scale-105'
                : 'text-[#74777d] hover:text-[#162839]'
            }`}
          >
            <span className="material-symbols-outlined text-[24px] mb-0.5">
              {tab.icon}
            </span>
            <span className="text-[10px] uppercase tracking-widest font-semibold">
              {tab.label}
            </span>
            {isActive && (
              <span className="absolute -bottom-1 w-1.5 h-1.5 bg-[#9a442a] rounded-full"></span>
            )}
          </button>
        );
      })}
    </nav>
  );
};
