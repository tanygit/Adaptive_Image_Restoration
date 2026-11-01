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
    warnings = [],
  } = data;

  const metrics = [
    { key: 'mean_brightness', label: 'Mean Brightness', unit: '/255' },
    { key: 'contrast_std', label: 'Contrast (Std Dev)', unit: '' },
    { key: 'sharpness_laplacian_var', label: 'Sharpness (Laplacian Var)', unit: '' },
    { key: 'noise_sigma_est', label: 'Estimated Noise (σ)', unit: '' },
  ];

  return (
    <div className="w-full max-w-5xl mx-auto mt-4 bg-studio-surface border border-studio-border rounded-2xl p-6 shadow-xl space-y-6">
      <div className="flex items-center justify-between border-b border-studio-border/60 pb-3">
        <div className="flex items-center space-x-2">
          <BarChart2 className="w-4 h-4 text-blue-400" />
          <h2 className="text-sm font-semibold tracking-wide text-white uppercase">
            Computer Vision Diagnostics & Pipeline Metrics
          </h2>
        </div>
        <div className="flex items-center space-x-1.5 text-xs text-studio-muted font-mono">
          <Clock className="w-3.5 h-3.5 text-slate-400" />
          <span>Total: {processing_time_seconds ? `${(processing_time_seconds * 1000).toFixed(0)} ms` : '--'}</span>
        </div>
      </div>

      {/* Grid: Quality Stats & Applied Operations */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Quality Metrics */}
        <div>
          <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-3">
            Heuristic Quality Comparison
          </h3>
          <div className="bg-studio-panel border border-studio-border rounded-xl overflow-hidden text-xs">
            <table className="w-full text-left">
              <thead className="bg-studio-border/30 text-studio-muted font-medium border-b border-studio-border">
                <tr>
                  <th className="py-2 px-3">Metric</th>
                  <th className="py-2 px-3">Before</th>
                  <th className="py-2 px-3">After</th>
                  <th className="py-2 px-3 text-right">Delta</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-studio-border/40 font-mono">
                {metrics.map(({ key, label }) => {
                  const beforeVal = quality_before[key];
                  const afterVal = quality_after[key];
                  const delta = quality_change[key];

                  return (
                    <tr key={key} className="hover:bg-studio-border/20 transition-colors">
                      <td className="py-2 px-3 text-slate-300 font-sans">{label}</td>
                      <td className="py-2 px-3 text-studio-muted">
                        {beforeVal !== undefined ? Number(beforeVal).toFixed(2) : '--'}
                      </td>
                      <td className="py-2 px-3 text-slate-200">
                        {afterVal !== undefined ? Number(afterVal).toFixed(2) : '--'}
                      </td>
                      <td className="py-2 px-3 text-right">
                        {delta !== undefined ? (
                          <span
                            className={
                              delta > 0
                                ? 'text-emerald-400 font-medium'
                                : delta < 0
                                ? 'text-amber-400 font-medium'
                                : 'text-slate-400'
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
          <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-3">
            OpenCV Operations Executed
          </h3>
          <div className="space-y-2">
            {selected_operations && selected_operations.length > 0 ? (
              selected_operations.map((op, idx) => (
                <div
                  key={idx}
                  className="p-3 rounded-xl bg-studio-panel border border-studio-border text-xs"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-semibold text-blue-300 font-mono">
                      {op.operation}
                    </span>
                    <span className="text-[11px] px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 uppercase tracking-wider">
                      {op.degradation}
                    </span>
                  </div>
                  <p className="text-studio-muted">{op.reason}</p>
                </div>
              ))
            ) : (
              <p className="text-xs text-studio-muted italic p-3 bg-studio-panel rounded-xl border border-studio-border">
                No operations applied to this image.
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Latency Timing Breakdown */}
      {timing_seconds && Object.keys(timing_seconds).length > 0 && (
        <div className="pt-2">
          <div className="flex items-center space-x-2 mb-2">
            <Cpu className="w-3.5 h-3.5 text-studio-muted" />
            <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
              Execution Time Breakdown
            </h3>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
            {Object.entries(timing_seconds).map(([phase, seconds]) => (
              <div key={phase} className="p-2.5 rounded-lg bg-studio-panel border border-studio-border">
                <span className="text-[11px] text-studio-muted capitalize block truncate">
                  {phase.replace(/_/g, ' ')}
                </span>
                <span className="font-mono font-medium text-slate-200">
                  {(seconds * 1000).toFixed(1)} ms
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Disclaimers & Limitations */}
      {limitations && limitations.length > 0 && (
        <div className="pt-3 border-t border-studio-border/60">
          <div className="flex items-start space-x-2 text-[11px] text-studio-muted">
            <ShieldAlert className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-slate-300 mb-0.5">Scientific Limitations & Notes:</p>
              <ul className="list-disc list-inside space-y-0.5">
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

