import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Columns, Split, ArrowLeftRight, Eye, AlertTriangle } from 'lucide-react';

export default function ComparisonSlider({ originalUrl, restoredUrl, filename }) {
  const [sliderPos, setSliderPos] = useState(50);
  const [isDragging, setIsDragging] = useState(false);
  const [viewMode, setViewMode] = useState('split'); // 'split' | 'side-by-side'
  const [isPressingOriginal, setIsPressingOriginal] = useState(false);
  const [imageError, setImageError] = useState(false);
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

  // Comprehensive keyboard navigation
  const handleKeyDown = (e) => {
    if (e.key === 'ArrowLeft') {
      e.preventDefault();
      setSliderPos((prev) => Math.max(0, prev - 3));
    } else if (e.key === 'ArrowRight') {
      e.preventDefault();
      setSliderPos((prev) => Math.min(100, prev + 3));
    } else if (e.key === 'PageDown') {
      e.preventDefault();
      setSliderPos((prev) => Math.max(0, prev - 10));
    } else if (e.key === 'PageUp') {
      e.preventDefault();
      setSliderPos((prev) => Math.min(100, prev + 10));
    } else if (e.key === 'Home') {
      e.preventDefault();
      setSliderPos(0);
    } else if (e.key === 'End') {
      e.preventDefault();
      setSliderPos(100);
    } else if (e.key === ' ' || e.key === '\\') {
      // Space or backslash toggles peek
      e.preventDefault();
      setIsPressingOriginal(true);
    }
  };

  const handleKeyUp = (e) => {
    if (e.key === ' ' || e.key === '\\') {
      e.preventDefault();
      setIsPressingOriginal(false);
    }
  };

  return (
    <div className="w-full flex flex-col items-center relative z-10">
      {/* Top View Mode & Peek Controls */}
      <div className="w-full max-w-5xl flex flex-wrap items-center justify-between gap-2.5 mb-3.5 px-2">
        <div className="flex items-center space-x-2">
          <span className="px-2.5 py-1 rounded-md bg-paper-warm border border-ink-dark/15 text-xs font-mono font-medium text-ink-muted truncate max-w-xs shadow-sm">
            {filename}
          </span>
        </div>

        <div className="flex items-center space-x-2.5">
          {/* Peek Original Button */}
          <button
            type="button"
            aria-pressed={isPressingOriginal}
            aria-label="Hold to peek original degraded photo (or hold Spacebar when focused)"
            onMouseDown={() => setIsPressingOriginal(true)}
            onMouseUp={() => setIsPressingOriginal(false)}
            onTouchStart={() => setIsPressingOriginal(true)}
            onTouchEnd={() => setIsPressingOriginal(false)}
            className="flex items-center space-x-1.5 px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-paper-card hover:bg-pop-yellow text-ink-dark border border-ink-dark shadow-pop-sm active:translate-x-0.5 active:translate-y-0.5 active:shadow-none transition-all select-none"
          >
            <Eye className="w-3.5 h-3.5" aria-hidden="true" />
            <span>Hold to Peek</span>
          </button>

          {/* View Toggle */}
          <div className="flex items-center bg-paper-card border border-ink-dark rounded-lg p-0.5 shadow-pop-sm" role="group" aria-label="Comparison display mode">
            <button
              type="button"
              onClick={() => setViewMode('split')}
              aria-label="Switch to split curtain slider"
              title="Split Curtain Slider"
              className={`p-1.5 rounded-md text-xs transition-colors ${
                viewMode === 'split'
                  ? 'bg-pop-cyan text-white font-bold'
                  : 'text-ink-muted hover:text-ink-dark'
              }`}
            >
              <Split className="w-4 h-4" aria-hidden="true" />
            </button>
            <button
              type="button"
              onClick={() => setViewMode('side-by-side')}
              aria-label="Switch to side by side view"
              title="Side by Side"
              className={`p-1.5 rounded-md text-xs transition-colors ${
                viewMode === 'side-by-side'
                  ? 'bg-pop-cyan text-white font-bold'
                  : 'text-ink-muted hover:text-ink-dark'
              }`}
            >
              <Columns className="w-4 h-4" aria-hidden="true" />
            </button>
          </div>
        </div>
      </div>

      {/* Main Comparison Canvas */}
      {viewMode === 'split' ? (
        <div
          ref={containerRef}
          onPointerDown={handlePointerDown}
          onKeyDown={handleKeyDown}
          onKeyUp={handleKeyUp}
          tabIndex={0}
          role="slider"
          aria-label="Image restoration before and after split slider"
          aria-valuenow={Math.round(sliderPos)}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuetext={`${Math.round(sliderPos)}% original showing`}
          className="relative w-full max-w-5xl aspect-video max-h-[66vh] rounded-3xl overflow-hidden select-none bg-paper-warm border-[3px] border-ink-dark shadow-pop cursor-ew-resize focus:outline-none focus:ring-4 focus:ring-pop-cyan/30 touch-none"
        >
          {/* Base Layer: Restored (Sharp/Clean) */}
          <img
            src={isPressingOriginal ? originalUrl : restoredUrl}
            alt="Restored result"
            onError={() => setImageError(true)}
            className="absolute inset-0 w-full h-full object-contain pointer-events-none"
          />

          {/* Curtain Overlay: Original Degraded Image clipped to sliderPos */}
          {!isPressingOriginal && (
            <div
              className="absolute inset-0 overflow-hidden pointer-events-none"
              style={{ width: `${sliderPos}%` }}
            >
              <img
                src={originalUrl}
                alt="Original degraded"
                onError={() => setImageError(true)}
                className="absolute inset-0 w-full h-full object-contain max-w-none"
                style={{ width: containerRef.current ? `${containerRef.current.clientWidth}px` : '100%' }}
              />
            </div>
          )}

          {/* Draggable Divider Handle with Pop Graphic Styling */}
          {!isPressingOriginal && (
            <div
              className="absolute top-0 bottom-0 pointer-events-none z-10 touch-none"
              style={{ left: `${sliderPos}%` }}
            >
              {/* Divider vertical rule */}
              <div className="absolute top-0 bottom-0 -ml-[1.5px] w-[3px] bg-ink-dark shadow-sm" />

              {/* Circular pop handle */}
              <div
                className="absolute top-1/2 -mt-5 -ml-5 w-10 h-10 rounded-full bg-pop-yellow text-ink-dark border-2 border-ink-dark shadow-pop-sm flex items-center justify-center transition-transform active:scale-95"
                style={{ touchAction: 'none' }}
              >
                <ArrowLeftRight className="w-4 h-4 text-ink-dark font-black" aria-hidden="true" />
              </div>
            </div>
          )}

          {/* Image Loading Error Fallback Overlay */}
          {imageError && (
            <div className="absolute inset-0 z-30 bg-paper-base/95 backdrop-blur-sm flex flex-col items-center justify-center p-6 text-center">
              <div className="w-10 h-10 rounded-xl bg-pop-magenta text-white flex items-center justify-center border border-ink-dark shadow-pop-sm mb-3">
                <AlertTriangle className="w-5 h-5" aria-hidden="true" />
              </div>
              <p className="font-bold text-sm text-ink-dark">Unable to render preview image</p>
              <p className="text-xs text-ink-muted mt-1 max-w-sm">The image file or restored buffer could not be decoded by the browser.</p>
            </div>
          )}

          {/* Watermark Tags */}
          <div className="absolute bottom-4 left-4 z-20 pointer-events-none">
            <span className="px-3 py-1 rounded-md text-xs font-bold bg-paper-base/90 backdrop-blur-md border border-ink-dark text-ink-dark shadow-sm">
              BEFORE (ORIGINAL)
            </span>
          </div>
          <div className="absolute bottom-4 right-4 z-20 pointer-events-none">
            <span className="px-3 py-1 rounded-md text-xs font-bold bg-pop-cyan text-white border-2 border-ink-dark shadow-pop-sm">
              AFTER (RESTORED)
            </span>
          </div>
        </div>
      ) : (
        /* Side by Side Mode */
        <div className="w-full max-w-5xl grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="relative aspect-video max-h-[58vh] rounded-2xl overflow-hidden bg-paper-warm border-2 border-ink-dark shadow-pop flex items-center justify-center">
            <img src={originalUrl} alt="Original degraded photo" className="w-full h-full object-contain" />
            <span className="absolute bottom-3 left-3 px-3 py-1 rounded-md text-xs font-bold bg-paper-base/90 backdrop-blur border border-ink-dark text-ink-dark">
              Original
            </span>
          </div>
          <div className="relative aspect-video max-h-[58vh] rounded-2xl overflow-hidden bg-paper-warm border-2 border-ink-dark shadow-pop flex items-center justify-center">
            <img src={restoredUrl} alt="Restored clear photo" className="w-full h-full object-contain" />
            <span className="absolute bottom-3 right-3 px-3 py-1 rounded-md text-xs font-bold bg-pop-cyan text-white border-2 border-ink-dark shadow-pop-sm">
              Restored
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
