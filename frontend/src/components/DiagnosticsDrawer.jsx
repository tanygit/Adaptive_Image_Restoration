import React from 'react';
import { Clock, Cpu, BarChart2, ShieldAlert } from 'lucide-react';

export default function DiagnosticsDrawer({ data }) {
  if (!data) return null;

  const {
    quality_before = {},
    quality_after = {},
    quality_change = {},
    selected_operations = [],
    timing_seconds = {},
    processing_time_seconds,
    limitations = [],
  } = data;

  const metrics = [
    { key: 'mean_brightness', label: 'Mean Brightness', unit: '/255' },
    { key: 'contrast_std', label: 'Contrast (Std Dev)', unit: '' },
    { key: 'sharpness_laplacian_var', label: 'Sharpness (Laplacian Var)', unit: '' },
    { key: 'noise_sigma_est', label: 'Estimated Noise (σ)', unit: '' },
  ];

  return (
    <div id="diagnostics-drawer" className="w-full max-w-5xl mx-auto mt-4 bg-paper-card border-2 border-ink-dark rounded-3xl p-6 shadow-pop relative z-10 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between border-b-2 border-ink-dark/10 pb-3.5">
        <div className="flex items-center space-x-2.5">
          <div className="w-7 h-7 rounded-lg bg-pop-cyan text-white flex items-center justify-center border border-ink-dark" aria-hidden="true">
            <BarChart2 className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-sm font-black tracking-wide text-ink-dark uppercase">
              Scientific Diagnostics & Quality Delta
            </h2>
            <p className="text-[11px] text-ink-muted">Deterministic Computer Vision Measurements</p>
          </div>
        </div>
        <div className="flex items-center space-x-1.5 text-xs font-mono font-bold px-3 py-1 bg-paper-warm border border-ink-dark/20 rounded-full text-ink-dark">
          <Clock className="w-3.5 h-3.5 text-pop-magenta" aria-hidden="true" />
          <span>{processing_time_seconds ? `${(processing_time_seconds * 1000).toFixed(0)} ms total` : '--'}</span>
        </div>
      </div>

      {/* Grid: Quality Stats & Applied Operations */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Quality Metrics Table (Polished for High WCAG AA Contrast) */}
        <div>
          <h3 className="text-xs font-black text-ink-dark uppercase tracking-wider mb-2.5">
            Objective Image Statistics
          </h3>
          <div className="bg-paper-warm border border-ink-dark/20 rounded-2xl overflow-hidden text-xs shadow-sm">
            <table className="w-full text-left" aria-label="Objective Image Quality Statistics Before and After Restoration">
              <thead className="bg-paper-muted/50 text-ink-muted font-bold border-b border-ink-dark/15">
                <tr>
                  <th scope="col" className="py-2.5 px-3.5">Metric</th>
                  <th scope="col" className="py-2.5 px-3">Before</th>
                  <th scope="col" className="py-2.5 px-3">After</th>
                  <th scope="col" className="py-2.5 px-3.5 text-right">Delta</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-ink-dark/10 font-mono">
                {metrics.map(({ key, label }) => {
                  const beforeVal = quality_before[key];
                  const afterVal = quality_after[key];
                  const delta = quality_change[key];

                  return (
                    <tr key={key} className="hover:bg-paper-muted/30 transition-colors">
                      <td className="py-2.5 px-3.5 text-ink-body font-sans font-medium">{label}</td>
                      <td className="py-2.5 px-3 text-ink-muted">
                        {beforeVal !== undefined ? Number(beforeVal).toFixed(2) : '--'}
                      </td>
                      <td className="py-2.5 px-3 text-ink-dark font-semibold">
                        {afterVal !== undefined ? Number(afterVal).toFixed(2) : '--'}
                      </td>
                      <td className="py-2.5 px-3.5 text-right">
                        {delta !== undefined ? (
                          <span
                            className={
                              delta > 0
                                ? 'inline-block px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-900 border border-emerald-300 font-bold'
                                : delta < 0
                                ? 'inline-block px-1.5 py-0.5 rounded bg-amber-100 text-amber-900 border border-amber-300 font-bold'
                                : 'text-ink-muted'
                            }
                          >
                            {delta > 0 ? `+${Number(delta).toFixed(2)}` : Number(delta).toFixed(2)}
                          </span>
                        ) : (
                          '--'
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Applied Operations */}
        <div>
          <h3 className="text-xs font-black text-ink-dark uppercase tracking-wider mb-2.5">
            Executed OpenCV Pipelines
          </h3>
          <div className="space-y-2.5">
            {selected_operations && selected_operations.length > 0 ? (
              selected_operations.map((op, idx) => (
                <div
                  key={idx}
                  className="p-3.5 rounded-2xl bg-paper-warm border border-ink-dark/20 text-xs shadow-sm"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-mono font-bold text-pop-cyan text-[13px]">
                      {op.operation}
                    </span>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-pink-100 text-pink-900 border border-pink-300 uppercase tracking-wider">
                      {op.degradation}
                    </span>
                  </div>
                  <p className="text-ink-body leading-relaxed">{op.reason}</p>
                </div>
              ))
            ) : (
              <p className="text-xs text-ink-muted italic p-4 bg-paper-warm rounded-2xl border border-ink-dark/20">
                No filters applied to this image.
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Latency Timing Breakdown */}
      {timing_seconds && Object.keys(timing_seconds).length > 0 && (
        <div className="pt-2">
          <div className="flex items-center space-x-2 mb-2">
            <Cpu className="w-3.5 h-3.5 text-pop-cyan" aria-hidden="true" />
            <h3 className="text-xs font-black text-ink-dark uppercase tracking-wider">
              Execution Latency Breakdown
            </h3>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs">
            {Object.entries(timing_seconds).map(([phase, seconds]) => (
              <div key={phase} className="p-3 rounded-xl bg-paper-warm border border-ink-dark/15 shadow-sm">
                <span className="text-[11px] font-bold text-ink-muted capitalize block truncate">
                  {phase.replace(/_/g, ' ')}
                </span>
                <span className="font-mono font-bold text-ink-dark">
                  {(seconds * 1000).toFixed(1)} ms
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Disclaimers & Limitations */}
      {limitations && limitations.length > 0 && (
        <div className="pt-3 border-t border-ink-dark/10">
          <div className="flex items-start space-x-2.5 text-[11px] text-ink-muted">
            <ShieldAlert className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" aria-hidden="true" />
            <div>
              <p className="font-bold text-ink-dark mb-0.5">Scientific Rigor & Constraints:</p>
              <ul className="list-disc list-inside space-y-0.5 leading-relaxed">
                {limitations.map((lim, i) => (
                  <li key={i}>{lim}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
