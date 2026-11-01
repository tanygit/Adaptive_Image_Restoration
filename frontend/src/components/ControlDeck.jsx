import React from 'react';
import { Download, Sliders, Activity, Sparkles, Check, Play } from 'lucide-react';

const DEGRADATION_LABELS = {
  low_light: 'Low Light Corrected',
  low_contrast: 'Contrast Balanced',
  gaussian_noise: 'Gaussian Denoised',
  salt_pepper_noise: 'Salt & Pepper Cleaned',
  blur: 'Sharpened',
};

export default function ControlDeck({
  detectedDegradations,
  currentStrength,
  selectedStrength,
  onStrengthChange,
  onApplyStrength,
  isProcessing,
  onDownload,
  onToggleDiagnostics,
  showDiagnostics,
}) {
  const hasChanges = selectedStrength !== currentStrength;

  return (
    <div className="w-full max-w-5xl mx-auto mt-6 bg-studio-surface border border-studio-border rounded-2xl p-4 sm:p-5 shadow-xl">
      {/* 1. Subtle Status Row */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-4 mb-4 border-b border-studio-border/60">
        <div className="flex items-center space-x-2">
          <Sparkles className="w-4 h-4 text-blue-400" />
          <span className="text-xs font-semibold uppercase tracking-wider text-studio-muted">
            Detected Flaws & Applied Fixes:
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {detectedDegradations && detectedDegradations.length > 0 ? (
            detectedDegradations.map((deg) => (
              <span
                key={deg}
                className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-500/10 text-blue-300 border border-blue-500/20"
              >
                <Check className="w-3 h-3 text-blue-400" />
                <span>{DEGRADATION_LABELS[deg] || deg}</span>
              </span>
            ))
          ) : (
            <span className="text-xs text-slate-400 italic">
              No degradations exceeded thresholds (Original preserved)
            </span>
          )}
        </div>
      </div>

      {/* 2. Controls & Actions */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
        {/* Strength Selector */}
        <div className="flex items-center space-x-3">
          <span className="text-xs font-medium text-studio-muted whitespace-nowrap">
            Restoration Strength:
          </span>

          <div className="inline-flex p-1 rounded-xl bg-studio-panel border border-studio-border">
            {['gentle', 'balanced', 'strong'].map((strength) => (
              <button
                key={strength}
                type="button"
                onClick={() => onStrengthChange(strength)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition-all ${
                  selectedStrength === strength
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'text-slate-300 hover:text-white hover:bg-studio-border/50'
                }`}
              >
                {strength}
              </button>
            ))}
          </div>

          {/* Manual Apply Button */}
          <button
            type="button"
            onClick={onApplyStrength}
            disabled={!hasChanges || isProcessing}
            className={`flex items-center space-x-1 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              hasChanges && !isProcessing
                ? 'bg-blue-600 hover:bg-blue-500 text-white shadow-md animate-pulse'
                : 'bg-studio-panel border border-studio-border text-slate-500 cursor-not-allowed'
            }`}
          >
            <Play className="w-3 h-3 fill-current" />
            <span>Apply</span>
          </button>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center space-x-3">
          <button
            type="button"
            onClick={onToggleDiagnostics}
            className={`flex items-center space-x-1.5 px-3 py-2 rounded-xl text-xs font-medium border transition-colors ${
              showDiagnostics
                ? 'bg-studio-panel border-blue-500 text-blue-300'
                : 'bg-studio-panel border-studio-border text-slate-300 hover:text-white hover:border-slate-500'
            }`}
          >
            <Activity className="w-3.5 h-3.5" />
            <span>{showDiagnostics ? 'Hide Diagnostics' : 'Diagnostics'}</span>
          </button>

          <button
            type="button"
            onClick={onDownload}
            className="flex items-center space-x-2 px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-lg shadow-blue-600/20 transition-all hover:scale-[1.02] active:scale-[0.98]"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Download PNG</span>
          </button>
        </div>
      </div>
    </div>
  );
}

