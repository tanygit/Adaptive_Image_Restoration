import React from 'react';
import { Sliders, RefreshCw } from 'lucide-react';

export default function Header({ backendStatus, onReset, hasImage }) {
  return (
    <header className="relative z-20 border-b border-ink-dark/10 bg-paper-base/90 backdrop-blur-md px-6 py-4">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center space-x-3.5">
          <div className="relative w-11 h-11 rounded-2xl bg-pop-cyan text-white flex items-center justify-center shadow-pop-sm border-2 border-ink-dark">
            <Sliders className="w-5 h-5" />
            <span className="absolute -top-1 -right-1 w-3.5 h-3.5 rounded-full bg-pop-yellow border-2 border-ink-dark" />
          </div>
          <div>
            <div className="flex items-center space-x-2.5">
              <h1 className="text-base sm:text-lg font-black tracking-tight text-ink-dark uppercase">
                ADAPTIVE RESTORE
              </h1>
              <span className="hidden sm:inline-block px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-pop-yellow text-ink-dark border border-ink-dark shadow-pop-sm">
                PRO LAB
              </span>
            </div>
            <p className="text-xs text-ink-body font-medium hidden sm:block">
              Explainable OpenCV filters guided by deep CNN flaw diagnosis
            </p>
          </div>
        </div>

        {/* Status & Actions */}
        <div className="flex items-center space-x-3 sm:space-x-4">
          {/* Backend Connection Status */}
          <div className="flex items-center space-x-2 text-xs px-3.5 py-1.5 rounded-full bg-paper-card border-2 border-ink-dark shadow-pop-sm">
            {backendStatus === 'online' ? (
              <>
                <span className="w-2.5 h-2.5 rounded-full bg-pop-green animate-pulse" />
                <span className="text-ink-dark font-black tracking-wide text-[11px]">ONLINE</span>
              </>
            ) : backendStatus === 'checking' ? (
              <>
                <span className="w-2.5 h-2.5 rounded-full bg-pop-amber animate-ping" />
                <span className="text-ink-muted font-bold text-[11px]">CONNECTING...</span>
              </>
            ) : (
              <>
                <span className="w-2.5 h-2.5 rounded-full bg-pop-magenta" />
                <span className="text-pop-magenta font-black text-[11px]">OFFLINE</span>
              </>
            )}
          </div>

          {/* New Image / Reset Button */}
          {hasImage && (
            <button
              onClick={onReset}
              aria-label="Upload a new photo"
              className="flex items-center space-x-1.5 px-3.5 py-1.5 text-xs font-bold rounded-xl bg-pop-yellow hover:bg-yellow-400 text-ink-dark border-2 border-ink-dark shadow-pop-sm active:translate-x-0.5 active:translate-y-0.5 active:shadow-none transition-all"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>New Photo</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
