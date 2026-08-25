import React, { useState } from 'react';
import { ScreenId } from './types';
import { ScreenToday, type LookTier } from './components/ScreenToday';
import { ScreenWardrobe } from './components/ScreenWardrobe';
import { ScreenInspiration } from './components/ScreenInspiration';
import { ScreenArchive } from './components/ScreenArchive';
import { ScreenProfile } from './components/ScreenProfile';

export default function App() {
  const [currentScreen, setCurrentScreen] = useState<ScreenId>('today');
  const [expandedLooks, setExpandedLooks] = useState<Record<LookTier, boolean>>({
    safe: false,
    fresh: false,
    stretch: false,
  });

  const handleNavigate = (screen: ScreenId) => {
    setCurrentScreen(screen);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleLookExpandedChange = (tier: LookTier, expanded: boolean) => {
    setExpandedLooks((current) => ({ ...current, [tier]: expanded }));
  };

  return (
    <div className="min-h-screen bg-[#fbf9f4] text-[#1b1c19]">
      {currentScreen === 'today' && (
        <ScreenToday
          onNavigate={handleNavigate}
          expandedLooks={expandedLooks}
          onLookExpandedChange={handleLookExpandedChange}
        />
      )}
      {currentScreen === 'wardrobe' && (
        <ScreenWardrobe onNavigate={handleNavigate} />
      )}
      {currentScreen === 'inspiration' && (
        <ScreenInspiration onNavigate={handleNavigate} />
      )}
      {currentScreen === 'archive' && (
        <ScreenArchive onNavigate={handleNavigate} />
      )}
      {currentScreen === 'profile' && (
        <ScreenProfile onNavigate={handleNavigate} />
      )}
    </div>
  );
}
