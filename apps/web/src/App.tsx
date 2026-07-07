import { useContext, useEffect, useState } from 'react';
import type { CaptionResultResponse, VideoJobStatusResponse } from '@shared-types';
import { getJobResult, getJobStatus, uploadVideo, type UploadStreamEvent } from './api';
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
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadSuccessMessage, setUploadSuccessMessage] = useState<string | null>(null);
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
    setUploadProgress(0);
    setUploadSuccessMessage(null);
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
    let timer = 0;

    async function poll() {
      try {
        const nextStatus = await getJobStatus(jobId);
        if (cancelled) {
          return;
        }

        setStatus(nextStatus);

        if (nextStatus.status === 'completed') {
          window.clearInterval(timer);
          try {
            const nextResult = await getJobResult(jobId);
            if (!cancelled) {
              setResult(nextResult);
              setView({ kind: 'result', jobId });
            }
          } catch (resultError) {
            const message = resultError instanceof Error ? resultError.message : 'Result is not ready yet.';
            if (!cancelled) {
              if (message === 'Result is not ready yet.') {
                setUploadSuccessMessage('Worker stub completed. No caption result has been generated yet.');
                setError(null);
              } else {
                setError(message);
              }
            }
          }
          return;
        }

        if (nextStatus.status === 'failed') {
          window.clearInterval(timer);
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
    timer = window.setInterval(poll, 2000);

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
    setUploadProgress(0);
    setUploadSuccessMessage(null);
    setError(null);
    setStatus(null);
    setResult(null);

    try {
      const response = await uploadVideo(file, setUploadProgress, (event) => {
        console.log(`[upload stream] ${event.event}`, event);
        setUploadSuccessMessage(event.message);
        setView({ kind: 'status', jobId: event.jobId });
        setStatus((previousStatus) => mapStreamEventToStatus(event, file.name, previousStatus));
        if (event.event === 'failed') {
          setError(event.message);
        }
      });
      setUploadSuccessMessage((currentMessage) => currentMessage ?? 'Upload complete. Supabase storage confirmed the object metadata.');
      setView({ kind: 'status', jobId: response.jobId });
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : 'Upload failed.');
    } finally {
      setIsUploading(false);
    }
  }

  function handleReset() {
    setView(initialState);
    setUploadProgress(0);
    setUploadSuccessMessage(null);
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
        <UploadPage
          error={error}
          isUploading={isUploading}
          uploadProgress={uploadProgress}
          successMessage={uploadSuccessMessage}
          onUpload={handleUpload}
        />
      ) : null}

      {view.kind === 'status' && status ? (
        <JobStatusPage status={status} successMessage={uploadSuccessMessage} />
      ) : null}

      {view.kind === 'result' && result ? <ResultPage onReset={handleReset} result={result} /> : null}
    </main>
  );
}

function mapStreamEventToStatus(
  event: UploadStreamEvent,
  originalFilename: string,
  previousStatus: VideoJobStatusResponse | null
): VideoJobStatusResponse {
  const now = new Date().toISOString();

  return {
    id: event.jobId,
    status: mapWorkerEventToJobStatus(event.event),
    currentStep: event.step,
    progress: event.progress ?? previousStatus?.progress ?? 0,
    errorMessage: event.event === 'failed' ? event.message : '',
    originalFilename,
    createdAt: previousStatus?.createdAt ?? now,
    updatedAt: now
  };
}

function mapWorkerEventToJobStatus(eventName: string): VideoJobStatusResponse['status'] {
  if (eventName === 'queued' || eventName === 'worker_invoked' || eventName === 'worker_available') {
    return 'queued';
  }

  if (eventName === 'completed') {
    return 'completed';
  }

  if (eventName === 'failed') {
    return 'failed';
  }

  return 'processing';
}
