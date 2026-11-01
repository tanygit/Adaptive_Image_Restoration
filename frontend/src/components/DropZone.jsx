import React, { useRef, useState } from 'react';
import { UploadCloud, SunMedium, Contrast, Sparkles, Eye, ShieldAlert, Sparkle, Image as ImageIcon } from 'lucide-react';

export default function DropZone({ onFileSelect, disabled }) {
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef(null);

  const handleDragOver = (e) => {
    e.preventDefault();
    if (!disabled) setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (disabled) return;

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      if (file.type.startsWith('image/')) {
        onFileSelect(file);
      }
    }
  };

  const handleInputChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      onFileSelect(e.target.files[0]);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      fileInputRef.current?.click();
    }
  };

  // Helper to load a synthetic degraded test image for instant demo
  const loadSyntheticSample = (type) => {
    const canvas = document.createElement('canvas');
    canvas.width = 640;
    canvas.height = 420;
    const ctx = canvas.getContext('2d');

    // Create scene
    const grad = ctx.createLinearGradient(0, 0, 640, 420);
    grad.addColorStop(0, '#1a1c2e');
    grad.addColorStop(0.5, '#4b3f72');
    grad.addColorStop(1, '#ff6b6b');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 640, 420);

    // Architectural silhouettes
    ctx.fillStyle = '#0f111a';
    ctx.fillRect(50, 200, 100, 220);
    ctx.fillRect(180, 140, 140, 280);
    ctx.fillRect(350, 180, 90, 240);
    ctx.fillRect(470, 230, 120, 190);

    // Windows
    ctx.fillStyle = '#ffd166';
    for (let y = 160; y < 380; y += 30) {
      for (let x = 200; x < 300; x += 25) {
        if (Math.random() > 0.3) ctx.fillRect(x, y, 14, 18);
      }
    }

    if (type === 'low_light') {
      // Darken significantly
      ctx.fillStyle = 'rgba(0, 0, 0, 0.75)';
      ctx.fillRect(0, 0, 640, 420);
    } else if (type === 'blur') {
      // Blur simulation
      ctx.filter = 'blur(6px)';
      ctx.drawImage(canvas, 0, 0);
      ctx.filter = 'none';
    } else if (type === 'noise') {
      // Add noise
      const imgData = ctx.getImageData(0, 0, 640, 420);
      const d = imgData.data;
      for (let i = 0; i < d.length; i += 4) {
        const noise = (Math.random() - 0.5) * 80;
        d[i] = Math.min(255, Math.max(0, d[i] + noise));
        d[i + 1] = Math.min(255, Math.max(0, d[i + 1] + noise));
        d[i + 2] = Math.min(255, Math.max(0, d[i + 2] + noise));
      }
      ctx.putImageData(imgData, 0, 0);
    }

    canvas.toBlob((blob) => {
      if (blob) {
        const testFile = new File([blob], `sample_${type}.png`, { type: 'image/png' });
        onFileSelect(testFile);
      }
    }, 'image/png');
  };

  return (
    <div className="w-full max-w-3xl mx-auto my-auto p-4 sm:p-6 relative z-10">
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        onKeyDown={handleKeyDown}
        tabIndex={0}
        role="button"
        aria-label="Drop your degraded image here or click to browse files"
        className={`relative cursor-pointer rounded-3xl border-[3px] border-ink-dark bg-paper-card p-8 sm:p-12 text-center transition-all duration-200 shadow-pop hover:shadow-pop-lg focus:outline-none focus:ring-4 focus:ring-pop-cyan/30 ${
          isDragging
            ? 'bg-pop-yellow/20 scale-[1.01] border-pop-cyan ring-4 ring-pop-cyan/20'
            : 'hover:-translate-y-0.5'
        } ${disabled ? 'opacity-50 pointer-events-none' : ''}`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          onChange={handleInputChange}
          className="sr-only"
          tabIndex={-1}
        />

        {/* Tactile Halftone Corner Accent */}
        <div className="absolute top-4 right-4 w-16 h-16 bg-halftone opacity-30 pointer-events-none rounded-xl" />

        {/* Central Icon: Optical Aperture in Vibrant Pop-Yellow */}
        <div className="relative w-20 h-20 mx-auto mb-5 rounded-2xl bg-pop-yellow border-2 border-ink-dark flex items-center justify-center shadow-pop-sm group">
          <UploadCloud className="w-10 h-10 text-ink-dark relative z-10 transition-transform group-hover:scale-110" aria-hidden="true" />
          <span className="absolute -bottom-1 -right-1 w-4 h-4 rounded-full bg-pop-cyan border border-ink-dark" />
          <span className="absolute -top-1 -left-1 w-3 h-3 rounded-full bg-pop-magenta border border-ink-dark" />
        </div>

        <h2 className="text-2xl sm:text-3xl font-black text-ink-dark mb-2 tracking-tight uppercase">
          Drop your degraded photo here
        </h2>
        <p className="text-sm text-ink-body font-medium mb-6 max-w-md mx-auto leading-relaxed">
          Restore underexposed lighting, flat contrast, sensor grain, or motion blur. Pure explainable OpenCV restoration in a single click.
        </p>

        {/* Vibrant Matte Action Button */}
        <span
          className="inline-flex items-center space-x-2.5 px-7 py-3.5 rounded-2xl bg-pop-cyan hover:bg-blue-600 text-white font-black text-sm tracking-wide border-2 border-ink-dark shadow-pop hover:shadow-pop-lg active:translate-x-0.5 active:translate-y-0.5 active:shadow-none transition-all select-none"
        >
          <Sparkle className="w-4 h-4 text-pop-yellow fill-current" aria-hidden="true" />
          <span>SELECT PHOTO FROM DEVICE</span>
        </span>

        {/* Degradation Capability Pills with Distinct Color Accents */}
        <div className="mt-10 pt-7 border-t-2 border-ink-dark/10">
          <p className="text-[11px] font-black tracking-widest uppercase text-ink-muted mb-3.5">
            5 Auto-Diagnosed Flaw Pipelines
          </p>
          <div className="flex flex-wrap justify-center gap-2">
            <span className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-amber-100 text-amber-950 font-bold text-xs border border-amber-300 shadow-sm">
              <SunMedium className="w-3.5 h-3.5 text-amber-600" aria-hidden="true" />
              <span>Low Light</span>
            </span>
            <span className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-blue-100 text-blue-950 font-bold text-xs border border-blue-300 shadow-sm">
              <Contrast className="w-3.5 h-3.5 text-blue-600" aria-hidden="true" />
              <span>Low Contrast</span>
            </span>
            <span className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-pink-100 text-pink-950 font-bold text-xs border border-pink-300 shadow-sm">
              <Sparkles className="w-3.5 h-3.5 text-pink-600" aria-hidden="true" />
              <span>Gaussian Noise</span>
            </span>
            <span className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-purple-100 text-purple-950 font-bold text-xs border border-purple-300 shadow-sm">
              <ShieldAlert className="w-3.5 h-3.5 text-purple-600" aria-hidden="true" />
              <span>Salt & Pepper</span>
            </span>
            <span className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-emerald-100 text-emerald-950 font-bold text-xs border border-emerald-300 shadow-sm">
              <Eye className="w-3.5 h-3.5 text-emerald-600" aria-hidden="true" />
              <span>Soft Blur</span>
            </span>
          </div>
        </div>

        {/* 1-Click Instant Demo Presets */}
        <div className="mt-6 pt-5 border-t border-ink-dark/10 flex flex-wrap items-center justify-center gap-2">
          <span className="text-xs font-bold text-ink-muted mr-1">Or test a sample:</span>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              loadSyntheticSample('low_light');
            }}
            className="px-2.5 py-1 rounded-lg text-xs font-bold bg-paper-warm hover:bg-pop-yellow text-ink-dark border border-ink-dark/30 shadow-sm transition-all"
          >
            🌙 Low-Light Sunset
          </button>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              loadSyntheticSample('blur');
            }}
            className="px-2.5 py-1 rounded-lg text-xs font-bold bg-paper-warm hover:bg-pop-cyan hover:text-white text-ink-dark border border-ink-dark/30 shadow-sm transition-all"
          >
            💨 Blurry Street
          </button>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              loadSyntheticSample('noise');
            }}
            className="px-2.5 py-1 rounded-lg text-xs font-bold bg-paper-warm hover:bg-pop-magenta hover:text-white text-ink-dark border border-ink-dark/30 shadow-sm transition-all"
          >
            📺 Grainy Frame
          </button>
        </div>
      </div>
    </div>
  );
}
