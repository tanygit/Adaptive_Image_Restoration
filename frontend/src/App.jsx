import React, { useState, useEffect, useCallback } from 'react';
import Header from './components/Header';
import DropZone from './components/DropZone';
import ComparisonSlider from './components/ComparisonSlider';
import ControlDeck from './components/ControlDeck';
import DiagnosticsDrawer from './components/DiagnosticsDrawer';
import BackgroundArtwork from './components/BackgroundArtwork';
import { Loader2, AlertTriangle, X, RefreshCw, Info } from 'lucide-react';

const API_BASE = 'http://127.0.0.1:8000';
const MAX_UPLOAD_BYTES = 25 * 1024 * 1024; // 25 MiB matches backend config

export default function App() {
  const [backendStatus, setBackendStatus] = useState('checking'); // 'checking' | 'online' | 'offline'
  const [file, setFile] = useState(null);
  const [originalUrl, setOriginalUrl] = useState(null);
  const [restoredUrl, setRestoredUrl] = useState(null);
  const [restoreData, setRestoreData] = useState(null);

  const [selectedStrength, setSelectedStrength] = useState('balanced');
  const [currentStrength, setCurrentStrength] = useState('balanced');
  const [isProcessing, setIsProcessing] = useState(false);
  const [showDiagnostics, setShowDiagnostics] = useState(false);
  const [error, setError] = useState(null);

  // Health check on mount & periodic polling
  const checkHealth = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/health`);
      if (res.ok) {
        const data = await res.json();
        setBackendStatus(data.status === 'ok' ? 'online' : 'offline');
      } else {
        setBackendStatus('offline');
      }
    } catch {
      setBackendStatus('offline');
    }
  }, []);

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 15000);
    return () => clearInterval(interval);
  }, [checkHealth]);

  // Clean up object URLs on unmount
  useEffect(() => {
    return () => {
      if (originalUrl) URL.revokeObjectURL(originalUrl);
    };
  }, [originalUrl]);

  // Global clipboard paste listener (Ctrl+V)
  useEffect(() => {
    const handlePaste = (e) => {
      if (isProcessing) return;
      const items = e.clipboardData?.items;
      if (!items) return;

      for (let i = 0; i < items.length; i++) {
        if (items[i].type.startsWith('image/')) {
          const pastedFile = items[i].getAsFile();
          if (pastedFile) {
            handleFileSelect(pastedFile);
            break;
          }
        }
      }
    };

    window.addEventListener('paste', handlePaste);
    return () => window.removeEventListener('paste', handlePaste);
  }, [isProcessing]);

  const handleFileSelect = async (selectedFile) => {
    setError(null);

    // Client-side file size guard
    if (selectedFile.size > MAX_UPLOAD_BYTES) {
      setError(`File exceeds the 25 MiB limit (${(selectedFile.size / (1024 * 1024)).toFixed(1)} MiB). Please choose a smaller image.`);
      return;
    }

    // Revoke previous object URL if any
    if (originalUrl) {
      URL.revokeObjectURL(originalUrl);
    }

    setFile(selectedFile);
    const localUrl = URL.createObjectURL(selectedFile);
    setOriginalUrl(localUrl);

    // Trigger restoration with default/selected strength
    await processRestoration(selectedFile, selectedStrength);
  };

  const processRestoration = async (fileToProcess, strength) => {
    setIsProcessing(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', fileToProcess);

      const res = await fetch(`${API_BASE}/restore?strength=${strength}&response_image=auto`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.error?.message || `Restoration failed with HTTP status ${res.status}`);
      }

      const data = await res.json();
      setRestoreData(data);
      setCurrentStrength(data.strength);
      setSelectedStrength(data.strength);

      // Resolve restored image URL
      if (data.restored_image_base64) {
        setRestoredUrl(`data:${data.restored_image_media_type};base64,${data.restored_image_base64}`);
      } else {
        setRestoredUrl(`${API_BASE}${data.restored_image_url}`);
      }
    } catch (err) {
      setError(err.message || 'Failed to restore image. Please ensure the backend is running at http://127.0.0.1:8000');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleApplyStrength = () => {
    if (file && selectedStrength !== currentStrength) {
      processRestoration(file, selectedStrength);
    }
  };

  const handleDownload = () => {
    if (!restoredUrl) return;
    const a = document.createElement('a');
    a.href = restoredUrl;
    a.download = `restored_${file?.name || 'image.png'}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  const handleReset = () => {
    if (originalUrl) URL.revokeObjectURL(originalUrl);
    setFile(null);
    setOriginalUrl(null);
    setRestoredUrl(null);
    setRestoreData(null);
    setSelectedStrength('balanced');
    setCurrentStrength('balanced');
    setShowDiagnostics(false);
    setError(null);
  };

  return (
    <div className="min-h-screen flex flex-col bg-paper-base text-ink-dark relative selection:bg-pop-magenta selection:text-white">
      {/* Pop Art Generative Background Artwork */}
      <BackgroundArtwork />

      <Header
        backendStatus={backendStatus}
        hasImage={!!file}
        onReset={handleReset}
      />

      <main className="flex-1 flex flex-col justify-center p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto w-full relative z-10">
        {/* Error Alert with Retry & Recovery */}
        {error && (
          <div
            role="alert"
            aria-live="assertive"
            className="w-full max-w-3xl mx-auto mb-6 p-4 rounded-2xl bg-paper-card border-2 border-pop-magenta text-ink-dark text-xs flex items-start justify-between shadow-pop-sm"
          >
            <div className="flex items-start space-x-3">
              <div className="w-6 h-6 rounded-md bg-pop-magenta text-white flex items-center justify-center shrink-0 mt-0.5">
                <AlertTriangle className="w-4 h-4" aria-hidden="true" />
              </div>
              <div>
                <p className="font-bold text-pop-magenta uppercase tracking-wide">Processing Interrupted</p>
                <p className="text-ink-body font-medium mt-0.5">{error}</p>
                {file && !restoredUrl && (
                  <button
                    type="button"
                    onClick={() => processRestoration(file, selectedStrength)}
                    className="mt-2.5 inline-flex items-center space-x-1.5 px-3 py-1 rounded-lg bg-pop-cyan text-white font-bold text-[11px] border border-ink-dark shadow-sm hover:bg-blue-600 active:translate-x-0.5 active:translate-y-0.5"
                  >
                    <RefreshCw className="w-3 h-3" />
                    <span>Retry Restoration</span>
                  </button>
                )}
              </div>
            </div>
            <button
              onClick={() => setError(null)}
              aria-label="Dismiss error message"
              className="p-1 hover:bg-paper-warm rounded-lg text-ink-muted hover:text-ink-dark"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Empty State: DropZone */}
        {(!file || (!restoredUrl && error)) && (
          <DropZone
            onFileSelect={handleFileSelect}
            disabled={backendStatus === 'offline'}
          />
        )}

        {/* Processing Loader Overlay */}
        {isProcessing && (
          <div
            role="status"
            aria-live="polite"
            className="fixed inset-0 z-50 bg-paper-base/75 backdrop-blur-md flex flex-col items-center justify-center space-y-4"
          >
            <div className="relative w-20 h-20 rounded-2xl bg-pop-yellow border-2 border-ink-dark flex items-center justify-center text-ink-dark shadow-pop">
              <Loader2 className="w-9 h-9 animate-spin" aria-hidden="true" />
              <span className="absolute -top-2 -right-2 w-5 h-5 rounded-full bg-pop-cyan border border-ink-dark" />
            </div>
            <div className="text-center px-4">
              <h3 className="text-lg font-black text-ink-dark uppercase tracking-wide">Restoring Image Clarity</h3>
              <p className="text-xs text-ink-muted mt-1 max-w-sm">
                Executing CNN diagnosis & running adaptive OpenCV pipelines...
              </p>
            </div>
          </div>
        )}

        {/* Active Comparison Canvas */}
        {file && originalUrl && restoredUrl && (
          <div className="flex-1 flex flex-col items-center justify-center w-full">
            <ComparisonSlider
              originalUrl={originalUrl}
              restoredUrl={restoredUrl}
              filename={file.name}
            />

            {/* Advisory Warnings from Backend Pipeline */}
            {restoreData?.warnings && restoreData.warnings.length > 0 && (
              <div className="w-full max-w-5xl mt-3 p-3 rounded-2xl bg-paper-card border border-amber-300 text-xs flex items-center space-x-2.5 shadow-sm text-ink-body">
                <Info className="w-4 h-4 text-amber-700 shrink-0" aria-hidden="true" />
                <span className="font-medium">{restoreData.warnings.join(' • ')}</span>
              </div>
            )}

            <ControlDeck
              detectedDegradations={restoreData?.detected_degradations || []}
              currentStrength={currentStrength}
              selectedStrength={selectedStrength}
              onStrengthChange={setSelectedStrength}
              onApplyStrength={handleApplyStrength}
              isProcessing={isProcessing}
              onDownload={handleDownload}
              onToggleDiagnostics={() => setShowDiagnostics((prev) => !prev)}
              showDiagnostics={showDiagnostics}
            />

            {showDiagnostics && <DiagnosticsDrawer data={restoreData} />}
          </div>
        )}
      </main>

      <footer className="relative z-10 border-t border-ink-dark/10 py-3.5 px-6 text-center text-xs font-medium text-ink-muted bg-paper-base/80 backdrop-blur">
        Adaptive Image Restoration &bull; Pop Art Craft Direction &bull; Explainable CV + Neural Classifier
      </footer>
    </div>
  );
}
