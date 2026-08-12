import React, { useState } from 'react';
import { ScreenId } from './types';
import { ScreenToday } from './components/ScreenToday';
import { ScreenWardrobe } from './components/ScreenWardrobe';
import { ScreenInspiration } from './components/ScreenInspiration';
import { ScreenArchive } from './components/ScreenArchive';
import { ScreenProfile } from './components/ScreenProfile';

export default function App() {
  const [currentScreen, setCurrentScreen] = useState<ScreenId>('today');

  const handleNavigate = (screen: ScreenId) => {
    setCurrentScreen(screen);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="min-h-screen bg-[#fbf9f4] text-[#1b1c19]">
      {currentScreen === 'today' && (
        <ScreenToday onNavigate={handleNavigate} />
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
