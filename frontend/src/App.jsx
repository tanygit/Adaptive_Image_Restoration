import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import DropZone from './components/DropZone';
import ComparisonSlider from './components/ComparisonSlider';
import ControlDeck from './components/ControlDeck';
import DiagnosticsDrawer from './components/DiagnosticsDrawer';
import { Loader2, AlertTriangle, X } from 'lucide-react';

const API_BASE = 'http://127.0.0.1:8000';

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

  // Health check on mount
  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  const checkHealth = async () => {
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
  };

  const handleFileSelect = async (selectedFile) => {
    setFile(selectedFile);
    setError(null);

    // Create object URL for local display of original image
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
      setError(err.message || 'Failed to restore image. Please ensure the backend is running.');
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
    <div className="min-h-screen flex flex-col bg-studio-bg text-slate-100">
      <Header
        backendStatus={backendStatus}
        hasImage={!!file}
        onReset={handleReset}
      />

      <main className="flex-1 flex flex-col justify-center p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto w-full">
        {/* Error Alert */}
        {error && (
          <div className="w-full max-w-3xl mx-auto mb-6 p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-start justify-between">
            <div className="flex items-start space-x-2.5">
              <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-rose-200">Processing Error</p>
                <p>{error}</p>
              </div>
            </div>
            <button
              onClick={() => setError(null)}
              className="p-1 hover:bg-rose-500/20 rounded-lg text-rose-400"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Empty State: DropZone */}
        {!file && (
          <DropZone
            onFileSelect={handleFileSelect}
            disabled={backendStatus === 'offline'}
          />
        )}

        {/* Processing Loader Overlay */}
        {isProcessing && (
          <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex flex-col items-center justify-center space-y-4">
            <div className="w-16 h-16 rounded-2xl bg-studio-panel border border-studio-border flex items-center justify-center text-blue-400 shadow-2xl">
              <Loader2 className="w-8 h-8 animate-spin" />
            </div>
            <div className="text-center">
              <h3 className="text-base font-semibold text-white">Analyzing & Restoring Image</h3>
              <p className="text-xs text-studio-muted mt-1">
                Evaluating CNN degradation features and applying matching OpenCV filters...
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

      <footer className="border-t border-studio-border/60 py-3 px-6 text-center text-xs text-studio-muted">
        Adaptive Image Restoration &bull; Explainable Classical CV Guided by Deep Learning
      </footer>
    </div>
  );
}

