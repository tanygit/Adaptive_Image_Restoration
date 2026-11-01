import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Columns, Split, ArrowLeftRight } from 'lucide-react';

export default function ComparisonSlider({ originalUrl, restoredUrl, filename }) {
  const [sliderPos, setSliderPos] = useState(50);
  const [isDragging, setIsDragging] = useState(false);
  const [viewMode, setViewMode] = useState('split'); // 'split' | 'side-by-side'
  const [isPressingOriginal, setIsPressingOriginal] = useState(false);
  const containerRef = useRef(null);

  const handleMove = useCallback((clientX) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const x = Math.max(0, Math.min(clientX - rect.left, rect.width));
    const percent = Math.max(0, Math.min((x / rect.width) * 100, 100));
    setSliderPos(percent);
  }, []);

  const handlePointerDown = (e) => {
    setIsDragging(true);
    handleMove(e.clientX);
  };

  const handlePointerMove = useCallback((e) => {
    if (!isDragging) return;
    handleMove(e.clientX);
  }, [isDragging, handleMove]);

  const handlePointerUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  useEffect(() => {
    if (isDragging) {
      window.addEventListener('pointermove', handlePointerMove);
      window.addEventListener('pointerup', handlePointerUp);
    }
    return () => {
      window.removeEventListener('pointermove', handlePointerMove);
      window.removeEventListener('pointerup', handlePointerUp);
    };
  }, [isDragging, handlePointerMove, handlePointerUp]);

  // Keyboard navigation
  const handleKeyDown = (e) => {
    if (e.key === 'ArrowLeft') {
      setSliderPos((prev) => Math.max(0, prev - 3));
    } else if (e.key === 'ArrowRight') {
      setSliderPos((prev) => Math.min(100, prev + 3));
    }
  };

  return (
    <div className="w-full flex flex-col items-center">
      {/* Top View Mode & Press-and-Hold Actions */}
      <div className="w-full max-w-5xl flex items-center justify-between mb-3 px-2">
        <div className="flex items-center space-x-2">
          <span className="text-xs text-studio-muted font-mono truncate max-w-xs">
            {filename}
          </span>
        </div>

        <div className="flex items-center space-x-2">
          <button
            type="button"
            onMouseDown={() => setIsPressingOriginal(true)}
            onMouseUp={() => setIsPressingOriginal(false)}
            onTouchStart={() => setIsPressingOriginal(true)}
            onTouchEnd={() => setIsPressingOriginal(false)}
            className="px-3 py-1 text-xs font-medium rounded-lg bg-studio-panel hover:bg-studio-border text-slate-300 border border-studio-border transition-colors select-none active:bg-blue-600/30 active:text-blue-200"
          >
            Hold to Peek Original
          </button>

          <div className="flex items-center bg-studio-panel border border-studio-border rounded-lg p-0.5">
            <button
              onClick={() => setViewMode('split')}
              title="Split Curtain Slider"
              className={`p-1.5 rounded-md text-xs transition-colors ${
                viewMode === 'split'
                  ? 'bg-blue-600 text-white'
                  : 'text-studio-muted hover:text-slate-200'
              }`}
            >
              <Split className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode('side-by-side')}
              title="Side by Side"
              className={`p-1.5 rounded-md text-xs transition-colors ${
                viewMode === 'side-by-side'
                  ? 'bg-blue-600 text-white'
                  : 'text-studio-muted hover:text-slate-200'
              }`}
            >
              <Columns className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Main Visual Display */}
      {viewMode === 'split' ? (
        <div
          ref={containerRef}
          onPointerDown={handlePointerDown}
          onKeyDown={handleKeyDown}
          tabIndex={0}
          className="relative w-full max-w-5xl aspect-video max-h-[68vh] rounded-2xl overflow-hidden select-none bg-black border border-studio-border shadow-2xl cursor-ew-resize focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {/* Base Layer: Restored Image */}
          <img
            src={isPressingOriginal ? originalUrl : restoredUrl}
            alt="Restored result"
            className="absolute inset-0 w-full h-full object-contain pointer-events-none"
          />

          {/* Curtain Overlay: Original Image clipped to sliderPos */}
          {!isPressingOriginal && (
            <div
              className="absolute inset-0 overflow-hidden pointer-events-none"
              style={{ width: `${sliderPos}%` }}
            >
              <img
                src={originalUrl}
                alt="Original degraded"
                className="absolute inset-0 w-full h-full object-contain max-w-none"
                style={{ width: containerRef.current ? `${containerRef.current.clientWidth}px` : '100%' }}
              />
            </div>
          )}

          {/* Draggable Divider Line & Handle */}
          {!isPressingOriginal && (
            <div
              className="absolute top-0 bottom-0 pointer-events-none z-10"
              style={{ left: `${sliderPos}%` }}
            >
              <div className="absolute top-0 bottom-0 -ml-[1px] w-[2px] bg-white shadow-[0_0_10px_rgba(0,0,0,0.7)]" />

              <div className="absolute top-1/2 -mt-5 -ml-5 w-10 h-10 rounded-full bg-white/95 text-slate-900 shadow-xl flex items-center justify-center border border-white backdrop-blur">
                <ArrowLeftRight className="w-4 h-4 text-slate-800" />
              </div>
            </div>
          )}

          {/* Badges */}
          <div className="absolute bottom-4 left-4 z-20 pointer-events-none">
            <span className="px-2.5 py-1 rounded-md text-xs font-semibold bg-black/70 backdrop-blur border border-white/10 text-slate-300 shadow">
              Original
            </span>
          </div>
          <div className="absolute bottom-4 right-4 z-20 pointer-events-none">
            <span className="px-2.5 py-1 rounded-md text-xs font-semibold bg-blue-600/80 backdrop-blur border border-blue-400/30 text-white shadow">
              Restored
            </span>
          </div>
        </div>
      ) : (
        /* Side by Side Mode */
        <div className="w-full max-w-5xl grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="relative aspect-video max-h-[60vh] rounded-2xl overflow-hidden bg-black border border-studio-border flex items-center justify-center">
            <img src={originalUrl} alt="Original" className="w-full h-full object-contain" />
            <span className="absolute bottom-3 left-3 px-2.5 py-1 rounded-md text-xs font-semibold bg-black/70 border border-white/10 text-slate-300">
              Original (Degraded)
            </span>
          </div>
          <div className="relative aspect-video max-h-[60vh] rounded-2xl overflow-hidden bg-black border border-studio-border flex items-center justify-center">
            <img src={restoredUrl} alt="Restored" className="w-full h-full object-contain" />
            <span className="absolute bottom-3 right-3 px-2.5 py-1 rounded-md text-xs font-semibold bg-blue-600/80 border border-blue-400/30 text-white">
              Restored
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

