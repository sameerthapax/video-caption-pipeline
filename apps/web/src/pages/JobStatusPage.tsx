import { useEffect, useState } from 'react';
import type { VideoJobStatusResponse } from '@shared-types';
import { ArrowSquareOut } from '@phosphor-icons/react';
import { Link, Navigate, useNavigate, useParams } from 'react-router-dom';
import { getJobResult, getJobStatus } from '../api';
import { BackButton } from '../components/BackButton';
import { JobStatusBadge } from '../components/JobStatusBadge';

const POLL_INTERVAL_MS = 2000;
//
export function JobStatusPage() {
  const { jobId } = useParams();
  const currentJobId = jobId ?? '';
  const navigate = useNavigate();
  const [status, setStatus] = useState<VideoJobStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!currentJobId) {
      return;
    }

    let cancelled = false;
    let timer = 0;

    async function poll() {
      try {
        const nextStatus = await getJobStatus(currentJobId);
        if (cancelled) {
          return;
        }

        setStatus(nextStatus);
        setError(null);
        setIsLoading(false);

        if (nextStatus.status === 'completed') {
          try {
            await getJobResult(currentJobId);
            if (!cancelled) {
              window.clearInterval(timer);
              navigate(`/jobs/${currentJobId}/result`, { replace: true });
            }
          } catch {
            if (!cancelled) {
              setError('The job completed, but the saved result is not ready yet.');
            }
          }
        }

        if (nextStatus.status === 'failed') {
          window.clearInterval(timer);
        }
      } catch (nextError) {
        if (!cancelled) {
          setError(nextError instanceof Error ? nextError.message : 'Could not load job status.');
          setIsLoading(false);
        }
      }
    }

    void poll();
    timer = window.setInterval(() => {
      void poll();
    }, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [currentJobId, navigate]);

  if (!currentJobId) {
    return <Navigate replace to="/" />;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <BackButton fallbackTo="/" />
      </div>

      <section className="grid gap-6 md:grid-cols-[1.1fr_0.9fr]">
        <article className="animate-fade-in rounded-xl border border-[var(--color-line)] bg-white p-8 md:p-10">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--color-muted)]">
                Job status
              </p>
              <h2 className="mt-4 text-3xl font-semibold tracking-[-0.05em] md:text-5xl">
                {status ? status.originalFilename : 'Loading job'}
              </h2>
            </div>
            {status ? <JobStatusBadge status={status.status} /> : null}
          </div>

          <div className="mt-8">
            {isLoading ? (
              <div className="space-y-4">
                <div className="h-2.5 rounded-full bg-[var(--color-surface-soft)]" />
                <div className="grid gap-4 md:grid-cols-2">
                  <DetailSkeleton />
                  <DetailSkeleton />
                  <DetailSkeleton />
                  <DetailSkeleton />
                </div>
              </div>
            ) : status ? (
              <>
                <div className="h-2.5 overflow-hidden rounded-full bg-[var(--color-surface-soft)]">
                  <div
                    className="h-full rounded-full bg-[var(--color-ink)] transition-[width] duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]"
                    style={{ width: `${status.progress}%` }}
                  />
                </div>
                <p className="mt-3 font-mono text-sm text-[var(--color-muted)]">
                  {status.progress}% complete
                </p>

                <dl className="mt-8 grid gap-4 md:grid-cols-2">
                  <DetailCard label="Job ID" value={status.id} />
                  <DetailCard label="Current step" value={status.currentStep} />
                  <DetailCard label="Created" value={formatDate(status.createdAt)} />
                  <DetailCard label="Updated" value={formatDate(status.updatedAt)} />
                </dl>
              </>
            ) : null}
          </div>

          {error ? (
            <p className="mt-6 rounded-md bg-[var(--color-tag-red-bg)] px-4 py-3 text-sm text-[var(--color-tag-red-text)]">
              {error}
            </p>
          ) : null}

          {status?.status === 'completed' ? (
            <div className="mt-6">
              <Link
                className="inline-flex min-h-12 items-center gap-2 rounded-md bg-[var(--color-ink)] px-5 text-sm font-medium text-white transition duration-200 ease-[cubic-bezier(0.16,1,0.3,1)] hover:bg-[#2f3437] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-ink)] active:scale-[0.98]"
                to={`/jobs/${currentJobId}/result`}
              >
                View result
                <ArrowSquareOut size={16} weight="bold" />
              </Link>
            </div>
          ) : null}
        </article>

        <aside className="grid gap-6">
          <article className="animate-fade-in rounded-xl border border-[var(--color-line)] bg-[var(--color-surface)] p-6">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--color-muted)]">
              Worker stages
            </p>
            <ol className="mt-5 space-y-3 text-sm leading-7 text-[var(--color-muted)]">
              <li>1. Upload verified and queued</li>
              <li>2. Preprocessing and extraction</li>
              <li>3. Temporal reasoning and summaries</li>
              <li>4. Styled caption generation</li>
              <li>5. Result saved for review</li>
            </ol>
          </article>

          <article className="animate-fade-in rounded-xl border border-[var(--color-line)] bg-white p-6">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--color-muted)]">
              Live note
            </p>
            <p className="mt-4 text-sm leading-7 text-[var(--color-muted)]">
              This page polls the API every {POLL_INTERVAL_MS / 1000} seconds and routes to the
              result page when the caption set is available.
            </p>
          </article>
        </aside>
      </section>
    </div>
  );
}

function DetailCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-[var(--color-line)] bg-[var(--color-surface)] p-4">
      <dt className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--color-muted)]">
        {label}
      </dt>
      <dd className="mt-3 break-all font-mono text-sm text-[var(--color-ink)]">{value}</dd>
    </div>
  );
}

function DetailSkeleton() {
  return (
    <div className="rounded-lg border border-[var(--color-line)] bg-[var(--color-surface)] p-4">
      <div className="h-3 w-16 rounded bg-[var(--color-surface-soft)]" />
      <div className="mt-3 h-4 w-full rounded bg-[var(--color-surface-soft)]" />
    </div>
  );
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}
