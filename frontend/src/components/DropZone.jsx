import React, { useRef, useState } from 'react';
import { UploadCloud, SunMedium, Contrast, Sparkles, Eye, ShieldAlert } from 'lucide-react';

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

  return (
    <div className="w-full max-w-3xl mx-auto my-auto p-6">
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`relative cursor-pointer rounded-2xl border-2 border-dashed p-12 text-center transition-all duration-200 ${
          isDragging
            ? 'border-blue-500 bg-blue-500/10 scale-[1.01]'
            : 'border-studio-border bg-studio-surface/50 hover:bg-studio-surface hover:border-slate-500'
        } ${disabled ? 'opacity-50 pointer-events-none' : ''}`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          onChange={handleInputChange}
          className="hidden"
        />

        <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-studio-panel border border-studio-border flex items-center justify-center text-blue-400 group-hover:scale-105 transition-transform">
          <UploadCloud className="w-8 h-8" />
        </div>

        <h3 className="text-xl font-medium text-white mb-2">
          Drop your degraded image here
        </h3>
        <p className="text-sm text-studio-muted mb-6 max-w-md mx-auto">
          Upload any photo with low lighting, washed-out contrast, digital noise, or slight blur. Supports JPEG, PNG, and WebP up to 10 MB.
        </p>

        <button
          type="button"
          className="px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-medium text-sm transition-colors shadow-lg shadow-blue-600/20"
        >
          Select from device
        </button>

        {/* Feature Pills */}
        <div className="mt-10 pt-8 border-t border-studio-border/60">
          <p className="text-xs font-semibold tracking-wider uppercase text-studio-muted mb-4">
            Adaptive CNN Detection Capabilities
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-studio-panel text-xs text-slate-300 border border-studio-border">
              <SunMedium className="w-3.5 h-3.5 text-amber-400" />
              <span>Low Light</span>
            </span>
            <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-studio-panel text-xs text-slate-300 border border-studio-border">
              <Contrast className="w-3.5 h-3.5 text-blue-400" />
              <span>Low Contrast</span>
            </span>
            <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-studio-panel text-xs text-slate-300 border border-studio-border">
              <Sparkles className="w-3.5 h-3.5 text-purple-400" />
              <span>Gaussian Noise</span>
            </span>
            <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-studio-panel text-xs text-slate-300 border border-studio-border">
              <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />
              <span>Salt & Pepper</span>
            </span>
            <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-studio-panel text-xs text-slate-300 border border-studio-border">
              <Eye className="w-3.5 h-3.5 text-emerald-400" />
              <span>Soft Blur</span>
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

