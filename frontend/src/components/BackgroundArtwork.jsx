import React from 'react';

export default function BackgroundArtwork() {
  return (
    <div className="fixed inset-0 pointer-events-none overflow-hidden z-0 select-none" aria-hidden="true">
      {/* 1. Tactile paper grain texture across entire viewport */}
      <div className="absolute inset-0 bg-grain pointer-events-none" />

      {/* 2. Vibrant Pop-Art Matte Color Shapes & Blobs (visible, alive, warm) */}
      {/* Top-Right: Saturated Pop Yellow Glow with Halftone Dots */}
      <div className="absolute -top-16 -right-16 w-96 h-96 rounded-full bg-pop-yellow/35 blur-2xl" />
      <div className="absolute -top-12 -right-12 w-80 h-80 rounded-full bg-halftone opacity-35" />

      {/* Bottom-Left: Electric Pop Cyan Wash with Cyan Halftone Screen */}
      <div className="absolute -bottom-24 -left-20 w-[420px] h-[420px] rounded-full bg-pop-cyan/25 blur-3xl" />
      <div className="absolute bottom-4 left-6 w-72 h-72 rounded-full bg-halftone-cyan opacity-40" />

      {/* Bottom-Right: Hot Pop Magenta Glow */}
      <div className="absolute -bottom-20 right-1/4 w-80 h-80 rounded-full bg-pop-magenta/20 blur-2xl" />
      <div className="absolute bottom-10 right-16 w-56 h-56 rounded-full bg-halftone-magenta opacity-30" />

      {/* Center Top: Subtle Warm Amber Tint */}
      <div className="absolute -top-28 left-1/3 w-80 h-80 rounded-full bg-pop-amber/15 blur-3xl" />

      {/* 3. Pop Art Print Registration Marks (+) in all 4 corners */}
      <div className="absolute top-6 left-6 hidden sm:flex items-center space-x-1.5 opacity-40">
        <div className="w-5 h-5 rounded-full border border-ink-dark flex items-center justify-center relative">
          <div className="absolute w-full h-[1px] bg-ink-dark" />
          <div className="absolute h-full w-[1px] bg-ink-dark" />
        </div>
        <span className="text-[9px] font-mono font-bold tracking-widest text-ink-dark">REG.01</span>
      </div>

      <div className="absolute top-6 right-6 hidden sm:flex items-center space-x-1.5 opacity-40">
        <span className="text-[9px] font-mono font-bold tracking-widest text-ink-dark">C-M-Y-K</span>
        <div className="w-5 h-5 rounded-full border border-ink-dark flex items-center justify-center relative">
          <div className="absolute w-full h-[1px] bg-ink-dark" />
          <div className="absolute h-full w-[1px] bg-ink-dark" />
        </div>
      </div>

      {/* 4. Blur vs Clear / Image Enhancer Optical Emblem (Top Left) */}
      <div className="absolute top-24 left-8 hidden xl:block opacity-75">
        <div className="relative p-3.5 rounded-2xl bg-paper-card border-2 border-ink-dark shadow-pop-sm flex flex-col items-center space-y-2">
          <div className="flex items-center space-x-2 text-[10px] font-mono font-bold uppercase text-ink-dark">
            <span className="w-2 h-2 rounded-full bg-pop-magenta animate-ping" />
            <span>OPTICAL LAB</span>
          </div>

          {/* Lens diagram: Left is blurred, right is crisp */}
          <div className="relative w-28 h-28 rounded-xl bg-paper-warm border border-ink-dark overflow-hidden flex">
            {/* Blurry half */}
            <div className="w-1/2 h-full bg-pop-magenta/20 backdrop-blur-sm flex flex-col items-center justify-center border-r border-dashed border-ink-dark/40 relative">
              <div className="w-8 h-8 rounded-full bg-pop-magenta/40 blur-[2px]" />
              <span className="absolute bottom-1 text-[8px] font-bold text-pop-magenta uppercase">BLUR</span>
            </div>

            {/* Sharp half */}
            <div className="w-1/2 h-full bg-pop-cyan/20 flex flex-col items-center justify-center relative">
              <div className="w-8 h-8 rounded-full border-2 border-pop-cyan flex items-center justify-center">
                <div className="w-2 h-2 rounded-full bg-pop-cyan" />
              </div>
              <span className="absolute bottom-1 text-[8px] font-bold text-pop-cyan uppercase">CLEAR</span>
            </div>
          </div>

          <div className="text-[9px] font-mono text-ink-muted tracking-tight text-center">
            ADAPTIVE RESTORATION
          </div>
        </div>
      </div>

      {/* 5. Print Proof CMYK Swatches Bar (Bottom Left) */}
      <div className="absolute bottom-8 left-8 hidden lg:flex items-center space-x-1.5 p-2 rounded-xl bg-paper-card border-2 border-ink-dark shadow-pop-sm opacity-85">
        <div className="w-4 h-4 rounded-md bg-pop-cyan border border-ink-dark shadow-sm" title="Cyan" />
        <div className="w-4 h-4 rounded-md bg-pop-magenta border border-ink-dark shadow-sm" title="Magenta" />
        <div className="w-4 h-4 rounded-md bg-pop-yellow border border-ink-dark shadow-sm" title="Yellow" />
        <div className="w-4 h-4 rounded-md bg-ink-dark border border-ink-dark shadow-sm" title="Key (Black)" />
        <span className="text-[10px] font-mono font-black text-ink-dark pl-1">PROOF OK</span>
      </div>

      {/* 6. Tactile Diffused-to-Restored Banner (Bottom Right) */}
      <div className="absolute bottom-8 right-8 hidden lg:flex items-center space-x-2.5 text-xs font-mono bg-paper-card px-4 py-2 rounded-2xl border-2 border-ink-dark shadow-pop-sm opacity-90">
        <span className="w-3 h-3 rounded-full bg-pop-magenta blur-[1px]" />
        <span className="font-bold text-ink-muted">DIFFUSED</span>
        <span className="text-ink-dark font-black text-sm">&rarr;</span>
        <span className="w-3 h-3 rounded-full bg-pop-cyan ring-2 ring-pop-cyan/30" />
        <span className="font-black text-pop-cyan">RESTORED</span>
      </div>
    </div>
  );
}
