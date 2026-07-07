import { useContext, useEffect, useState } from 'react';
import type { CaptionResultResponse, VideoJobStatusResponse } from '@shared-types';
import { getJobResult, getJobStatus, uploadVideo } from './api';
import { AuthContext } from './auth';
import { AuthGate } from './components/AuthGate';
import { JobStatusPage } from './pages/JobStatusPage';
import { ResultPage } from './pages/ResultPage';
import { UploadPage } from './pages/UploadPage';

type ViewState =
  | { kind: 'upload' }
  | { kind: 'status'; jobId: string }
  | { kind: 'result'; jobId: string };

const initialState: ViewState = { kind: 'upload' };

export default function App() {
  const { isReady, logout, user } = useContext(AuthContext);
  const [view, setView] = useState<ViewState>(initialState);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<VideoJobStatusResponse | null>(null);
  const [result, setResult] = useState<CaptionResultResponse | null>(null);

  const activeJobId = view.kind === 'upload' ? null : view.jobId;

  useEffect(() => {
    if (user) {
      return;
    }

    setView(initialState);
    setIsUploading(false);
    setError(null);
    setStatus(null);
    setResult(null);
  }, [user]);

  useEffect(() => {
    if (!user || view.kind !== 'status') {
      return;
    }

    const jobId = view.jobId;
    let cancelled = false;

    async function poll() {
      try {
        const nextStatus = await getJobStatus(jobId);
        if (cancelled) {
          return;
        }

        setStatus(nextStatus);

        if (nextStatus.status === 'completed') {
          const nextResult = await getJobResult(jobId);
          if (!cancelled) {
            setResult(nextResult);
            setView({ kind: 'result', jobId });
          }
          return;
        }

        if (nextStatus.status === 'failed') {
          setError(nextStatus.errorMessage || 'Pipeline failed.');
          return;
        }
      } catch (nextError) {
        if (!cancelled) {
          setError(nextError instanceof Error ? nextError.message : 'Polling failed.');
        }
      }
    }

    poll();
    const timer = window.setInterval(poll, 2000);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [user, view]);

  if (!isReady) {
    return (
      <main className="auth-shell">
        <section className="auth-card panel">
          <div className="eyebrow">Session</div>
          <h1>Checking authentication…</h1>
        </section>
      </main>
    );
  }

  if (!user) {
    return <AuthGate />;
  }

  async function handleUpload(file: File) {
    setIsUploading(true);
    setError(null);
    setStatus(null);
    setResult(null);

    try {
      const response = await uploadVideo(file);
      setView({ kind: 'status', jobId: response.jobId });
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : 'Upload failed.');
    } finally {
      setIsUploading(false);
    }
  }

  function handleReset() {
    setView(initialState);
    setStatus(null);
    setResult(null);
    setError(null);
  }

  return (
    <main className="app-shell">
      <header className="hero">
        <div>
          <div className="eyebrow">Video Caption Pipeline</div>
          <h1>Hackathon-ready caption generation without the production complexity yet.</h1>
        </div>
        <div className="hero-actions">
          <code className="job-chip">{user.email ?? user.id}</code>
          {activeJobId ? <code className="job-chip">Job: {activeJobId}</code> : null}
          <button className="secondary-button" onClick={() => void logout()} type="button">
            Log out
          </button>
        </div>
      </header>

      {view.kind === 'upload' ? (
        <UploadPage error={error} isUploading={isUploading} onUpload={handleUpload} />
      ) : null}

      {view.kind === 'status' && status ? <JobStatusPage status={status} /> : null}

      {view.kind === 'result' && result ? <ResultPage onReset={handleReset} result={result} /> : null}
    </main>
  );
}
