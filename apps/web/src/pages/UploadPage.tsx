import { useState, type FormEvent } from 'react';
import { FilmSlate, UploadSimple } from '@phosphor-icons/react';
import { useNavigate } from 'react-router-dom';
import { uploadVideo, type UploadStreamEvent } from '../api';
import { BackButton } from '../components/BackButton';

const ACCEPTED_EXTENSIONS = ['MP4', 'MOV', 'WEBM', 'M4V', 'MKV'];

export function UploadPage() {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [streamEvent, setStreamEvent] = useState<UploadStreamEvent | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!file) {
      setError('Choose a video file before queuing a job.');
      return;
    }

    setIsUploading(true);
    setUploadProgress(0);
    setError(null);
    setSuccessMessage(null);
    setStreamEvent(null);

    try {
      const response = await uploadVideo(file, setUploadProgress, (nextEvent) => {
        setStreamEvent(nextEvent);
        setSuccessMessage(nextEvent.message);
        if (nextEvent.event === 'failed') {
          setError(nextEvent.message);
        }
      });
      navigate(`/jobs/${response.jobId}`);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : 'Upload failed.');
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <BackButton fallbackTo="/" />
      </div>

      <section className="grid gap-6 md:grid-cols-[1.15fr_0.85fr]">
        <article className="animate-fade-in rounded-xl border border-[var(--color-line)] bg-white p-8 md:p-10">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--color-muted)]">
            Upload
          </p>
          <h2 className="mt-4 max-w-3xl text-4xl font-semibold tracking-[-0.05em] text-balance md:text-5xl">
            Send a video to storage and queue the caption pipeline.
          </h2>
          <p className="mt-5 max-w-2xl text-base leading-8 text-[var(--color-muted)]">
            The browser uploads directly to storage, then the API verifies the object and starts the
            worker flow.
          </p>

          <form className="mt-8 space-y-5" onSubmit={handleSubmit}>
            <label className="block rounded-xl border border-dashed border-[var(--color-line-strong)] bg-[var(--color-surface)] p-6 transition duration-200 ease-[cubic-bezier(0.16,1,0.3,1)] hover:border-[var(--color-ink)]">
              <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                <div>
                  <div className="inline-flex rounded-lg bg-white p-3 text-[var(--color-ink)]">
                    <FilmSlate size={24} weight="fill" />
                  </div>
                  <p className="mt-4 text-lg font-medium tracking-[-0.03em] text-[var(--color-ink)]">
                    Video file
                  </p>
                  <p className="mt-2 text-sm leading-7 text-[var(--color-muted)]">
                    Accepted formats: {ACCEPTED_EXTENSIONS.join(', ')}
                  </p>
                </div>
                <div className="min-w-0 md:max-w-xs">
                  <input
                    accept="video/*,.mp4,.mov,.webm,.m4v,.mkv"
                    className="block w-full text-sm text-[var(--color-muted)] file:mr-4 file:rounded-md file:border-0 file:bg-[var(--color-ink)] file:px-4 file:py-3 file:text-sm file:font-medium file:text-white hover:file:bg-[#2f3437]"
                    name="video"
                    onChange={(event) => {
                      setFile(event.target.files?.[0] ?? null);
                      setError(null);
                      setSuccessMessage(null);
                    }}
                    type="file"
                  />
                </div>
              </div>
            </label>

            {file ? (
              <div className="rounded-lg bg-[var(--color-surface)] px-4 py-3 text-sm text-[var(--color-muted)]">
                Selected file: <span className="font-medium text-[var(--color-ink)]">{file.name}</span>
              </div>
            ) : null}

            {isUploading ? (
              <div className="space-y-2">
                <div className="h-2.5 overflow-hidden rounded-full bg-[var(--color-surface-soft)]">
                  <div
                    className="h-full rounded-full bg-[var(--color-ink)] transition-[width] duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
                <p className="font-mono text-sm text-[var(--color-muted)]">Upload progress {uploadProgress}%</p>
              </div>
            ) : null}

            {streamEvent ? (
              <div className="rounded-lg bg-[var(--color-surface)] px-4 py-3 text-sm text-[var(--color-muted)]">
                <span className="font-mono text-[var(--color-ink)]">{streamEvent.step}</span> {' · '}
                {streamEvent.message}
              </div>
            ) : null}

            {error ? (
              <p className="rounded-md bg-[var(--color-tag-red-bg)] px-4 py-3 text-sm text-[var(--color-tag-red-text)]">
                {error}
              </p>
            ) : null}

            {successMessage ? (
              <p className="rounded-md bg-[var(--color-tag-green-bg)] px-4 py-3 text-sm text-[var(--color-tag-green-text)]">
                {successMessage}
              </p>
            ) : null}

            <button
              className="inline-flex min-h-12 items-center gap-2 rounded-md bg-[var(--color-ink)] px-5 text-sm font-medium text-white transition duration-200 ease-[cubic-bezier(0.16,1,0.3,1)] hover:bg-[#2f3437] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-ink)] active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-60"
              disabled={isUploading}
              type="submit"
            >
              <UploadSimple size={16} weight="bold" />
              {isUploading ? 'Uploading...' : 'Queue job'}
            </button>
          </form>
        </article>

        <aside className="grid gap-6">
          <article className="animate-fade-in rounded-xl border border-[var(--color-line)] bg-[var(--color-surface)] p-6">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--color-muted)]">
              Output set
            </p>
            <ul className="mt-5 space-y-4 text-sm leading-7 text-[var(--color-muted)]">
              <li>Formal for public-facing or presentation-safe delivery.</li>
              <li>Sarcastic for a dry alternate draft.</li>
              <li>Humorous tech for developer-facing voice.</li>
              <li>Humorous non-tech for broader audience phrasing.</li>
            </ul>
          </article>

          <article className="animate-fade-in rounded-xl border border-[var(--color-line)] bg-white p-6">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--color-muted)]">
              Suggested source clip
            </p>
            <p className="mt-4 text-sm leading-7 text-[var(--color-muted)]">
              Use a short recording with stable speech and visible scene changes while the worker
              pipeline is still expanding.
            </p>
          </article>
        </aside>
      </section>
    </div>
  );
}
