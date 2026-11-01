import React from 'react';
import { Download, Activity, Sparkles, Check, Play } from 'lucide-react';

const DEGRADATION_LABELS = {
  low_light: 'Low Light Boosted',
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
    <div className="w-full max-w-5xl mx-auto mt-6 bg-paper-card border-[3px] border-ink-dark rounded-3xl p-5 sm:p-6 shadow-pop relative z-10">
      {/* 1. Status Row */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-4 mb-4 border-b-2 border-ink-dark/10">
        <div className="flex items-center space-x-2">
          <div className="w-6 h-6 rounded-lg bg-pop-magenta text-white flex items-center justify-center border border-ink-dark shadow-sm">
            <Sparkles className="w-3.5 h-3.5 fill-current" />
          </div>
          <span className="text-xs font-black uppercase tracking-wider text-ink-dark">
            Diagnosed Defects & Applied Filters:
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-2" role="status" aria-live="polite">
          {detectedDegradations && detectedDegradations.length > 0 ? (
            detectedDegradations.map((deg) => (
              <span
                key={deg}
                className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-black bg-cyan-100 text-cyan-950 border border-cyan-400 shadow-sm"
              >
                <Check className="w-3.5 h-3.5 text-pop-cyan" aria-hidden="true" />
                <span>{DEGRADATION_LABELS[deg] || deg}</span>
              </span>
            ))
          ) : (
            <span className="text-xs text-ink-muted italic">
              No degradations exceeded thresholds (Original retained)
            </span>
          )}
        </div>
      </div>

      {/* 2. Controls & Actions */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
        {/* Strength Selector */}
        <div className="flex flex-wrap items-center gap-3">
          <span id="strength-group-label" className="text-xs font-bold uppercase tracking-wide text-ink-dark">
            Restoration Strength:
          </span>

          <div
            role="radiogroup"
            aria-labelledby="strength-group-label"
            className="inline-flex p-1 rounded-xl bg-paper-warm border border-ink-dark/20 shadow-inner"
          >
            {['gentle', 'balanced', 'strong'].map((strength) => {
              const isSelected = selectedStrength === strength;
              return (
                <button
                  key={strength}
                  type="button"
                  role="radio"
                  aria-checked={isSelected}
                  onClick={() => onStrengthChange(strength)}
                  className={`min-h-[38px] px-3.5 py-1.5 rounded-lg text-xs font-bold capitalize transition-all select-none ${
                    isSelected
                      ? 'bg-pop-yellow text-ink-dark border border-ink-dark shadow-pop-sm'
                      : 'text-ink-muted hover:text-ink-dark'
                  }`}
                >
                  {strength}
                </button>
              );
            })}
          </div>

          {/* Manual Apply Button (Smooth tactile pulse instead of distracting bounce) */}
          <button
            type="button"
            onClick={onApplyStrength}
            disabled={!hasChanges || isProcessing}
            aria-label={`Apply ${selectedStrength} strength restoration`}
            className={`min-h-[38px] flex items-center space-x-1.5 px-4 py-1.5 rounded-xl text-xs font-bold transition-all select-none ${
              hasChanges && !isProcessing
                ? 'bg-pop-cyan hover:bg-blue-600 text-white border-2 border-ink-dark shadow-pop-sm ring-2 ring-pop-cyan/40 ring-offset-1 cursor-pointer active:translate-x-0.5 active:translate-y-0.5 active:shadow-none'
                : 'bg-paper-warm border border-ink-dark/20 text-ink-muted/50 cursor-not-allowed'
            }`}
          >
            <Play className="w-3.5 h-3.5 fill-current" aria-hidden="true" />
            <span>Apply</span>
          </button>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center space-x-3">
          <button
            type="button"
            onClick={onToggleDiagnostics}
            aria-expanded={showDiagnostics}
            aria-controls="diagnostics-drawer"
            className={`min-h-[38px] flex items-center space-x-1.5 px-3.5 py-2 rounded-xl text-xs font-bold border-2 transition-all select-none ${
              showDiagnostics
                ? 'bg-pop-yellow border-ink-dark text-ink-dark shadow-pop-sm'
                : 'bg-paper-card border-ink-dark/20 text-ink-dark hover:border-ink-dark shadow-sm hover:shadow-pop-sm'
            }`}
          >
            <Activity className="w-3.5 h-3.5" aria-hidden="true" />
            <span>{showDiagnostics ? 'Hide Lab Specs' : 'Lab Specs'}</span>
          </button>

          <button
            type="button"
            onClick={onDownload}
            aria-label="Download restored image as PNG"
            className="min-h-[38px] flex items-center space-x-2 px-5 py-2 rounded-xl bg-pop-magenta hover:bg-pink-600 text-white text-xs font-black tracking-wide border-2 border-ink-dark shadow-pop hover:shadow-pop-lg active:translate-x-0.5 active:translate-y-0.5 active:shadow-none transition-all select-none"
          >
            <Download className="w-4 h-4" aria-hidden="true" />
            <span>DOWNLOAD PNG</span>
          </button>
        </div>
      </div>
    </div>
  );
}
