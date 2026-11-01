import React from 'react';
import { Sliders, RefreshCw, CheckCircle2, AlertCircle } from 'lucide-react';

export default function Header({ backendStatus, onReset, hasImage }) {
  return (
    <header className="border-b border-studio-border bg-studio-surface/80 backdrop-blur sticky top-0 z-30 px-6 py-4">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-lg bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400">
            <Sliders className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-lg font-semibold tracking-tight text-white">
              Adaptive Image Restoration
            </h1>
            <p className="text-xs text-studio-muted">
              Deep CNN flaw detection paired with deterministic OpenCV restoration
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          {/* Backend Connection Status */}
          <div className="flex items-center space-x-2 text-xs px-3 py-1.5 rounded-full bg-studio-panel border border-studio-border">
            {backendStatus === 'online' ? (
              <>
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                <span className="text-emerald-400 font-medium">Model Ready</span>
              </>
            ) : backendStatus === 'checking' ? (
              <>
                <span className="w-2 h-2 rounded-full bg-amber-500 animate-ping" />
                <span className="text-amber-400">Connecting...</span>
              </>
            ) : (
              <>
                <span className="w-2 h-2 rounded-full bg-rose-500" />
                <span className="text-rose-400 font-medium">Backend Offline</span>
              </>
            )}
          </div>

          {/* New Image / Reset Button */}
          {hasImage && (
            <button
              onClick={onReset}
              className="flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-studio-panel hover:bg-studio-border text-slate-200 transition-colors border border-studio-border"
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

