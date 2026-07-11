import { useEffect, useState } from 'react';
import type { CaptionResultResponse } from '@shared-types';
import { Copy, UploadSimple } from '@phosphor-icons/react';
import { Link, Navigate, useParams } from 'react-router-dom';
import { getJobResult } from '../api';
import { BackButton } from '../components/BackButton';
import { CaptionCard } from '../components/CaptionCard';

export function ResultPage() {
  const { jobId } = useParams();
  const currentJobId = jobId ?? '';
  const [result, setResult] = useState<CaptionResultResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<string | null>(null);

  useEffect(() => {
    if (!currentJobId) {
      return;
    }

    let cancelled = false;

    async function load() {
      try {
        const nextResult = await getJobResult(currentJobId);
        if (!cancelled) {
          setResult(nextResult);
          setError(null);
        }
      } catch (nextError) {
        if (!cancelled) {
          setError(nextError instanceof Error ? nextError.message : 'Could not load result.');
        }
      }
    }

    void load();

    return () => {
      cancelled = true;
    };
  }, [currentJobId]);

  if (!currentJobId) {
    return <Navigate replace to="/" />;
  }

  const cards = result
    ? [
        { label: 'Formal', tone: 'Public-safe voice', text: result.formalCaption },
        { label: 'Sarcastic', tone: 'Dry alternate draft', text: result.sarcasticCaption },
        { label: 'Humorous tech', tone: 'Developer-facing voice', text: result.humorousTechCaption },
        {
          label: 'Humorous non-tech',
          tone: 'General audience voice',
          text: result.humorousNonTechCaption,
        },
      ]
    : [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <BackButton fallbackTo={`/jobs/${currentJobId}`} />
          <Link
            className="inline-flex min-h-10 items-center gap-2 rounded-md border border-[var(--color-line)] bg-white px-3 text-sm text-[var(--color-muted)] transition duration-200 ease-[cubic-bezier(0.16,1,0.3,1)] hover:border-[var(--color-ink)] hover:text-[var(--color-ink)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-ink)] active:scale-[0.98]"
            to="/upload"
          >
          <UploadSimple size={16} weight="bold" />
          New upload
        </Link>
      </div>

      {error ? (
        <div className="rounded-xl border border-[var(--color-line)] bg-[var(--color-tag-red-bg)] px-5 py-4 text-sm text-[var(--color-tag-red-text)]">
          {error}
        </div>
      ) : null}

      <section className="grid gap-6 md:grid-cols-[1.15fr_0.85fr]">
        <article className="animate-fade-in rounded-xl border border-[var(--color-line)] bg-white p-8 md:p-10">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--color-muted)]">
                Neutral summary
              </p>
              <h2 className="mt-4 text-3xl font-semibold tracking-[-0.05em] md:text-5xl">
                Worker output is ready for review.
              </h2>
            </div>
            {result ? (
              <button
                className="inline-flex min-h-10 items-center gap-2 rounded-md border border-[var(--color-line)] bg-[var(--color-surface)] px-3 text-sm text-[var(--color-ink)] transition duration-200 ease-[cubic-bezier(0.16,1,0.3,1)] hover:border-[var(--color-ink)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-ink)] active:scale-[0.98]"
                onClick={() => void handleCopy(result.neutralSummary, 'Summary', setCopied)}
                type="button"
              >
                <Copy size={16} weight="bold" />
                {copied === 'Summary' ? 'Copied' : 'Copy summary'}
              </button>
            ) : null}
          </div>

          {result ? (
            <>
              <p className="mt-8 max-w-4xl text-base leading-8 text-[var(--color-ink)]">
                {result.neutralSummary}
              </p>
              <p className="mt-6 text-sm text-[var(--color-muted)]">
                Saved {formatDate(result.createdAt)}
              </p>
            </>
          ) : (
            <div className="mt-8 space-y-3">
              <div className="h-4 w-36 rounded bg-[var(--color-surface-soft)]" />
              <div className="h-4 w-full rounded bg-[var(--color-surface-soft)]" />
              <div className="h-4 w-full rounded bg-[var(--color-surface-soft)]" />
              <div className="h-4 w-3/4 rounded bg-[var(--color-surface-soft)]" />
            </div>
          )}
        </article>

        <aside className="grid gap-6">
          <article className="animate-fade-in rounded-xl border border-[var(--color-line)] bg-[var(--color-surface)] p-6">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--color-muted)]">
              Review notes
            </p>
            <ul className="mt-5 space-y-3 text-sm leading-7 text-[var(--color-muted)]">
              <li>Use the neutral summary as the factual anchor before selecting a tone.</li>
              <li>Check that humor variants preserve the original meaning of the clip.</li>
              <li>Completed captions remain tied to this job route for later review.</li>
            </ul>
          </article>
          <article className="animate-fade-in rounded-xl border border-[var(--color-line)] bg-white p-6">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--color-muted)]">
              Workflow
            </p>
            <p className="mt-4 text-sm leading-7 text-[var(--color-muted)]">
              This page reads the saved result from the API, so returning later should show the same
              caption set that was stored for the job.
            </p>
          </article>
        </aside>
      </section>

      <section className="grid gap-4 md:grid-cols-[1fr_1fr]">
        {result
          ? cards.map((card) => (
              <div key={card.label}>
                <div className="mb-3 flex items-center justify-between">
                  <p className="text-sm font-medium text-[var(--color-muted)]">{card.label}</p>
                  <button
                    className="text-sm text-[var(--color-muted)] underline-offset-4 hover:text-[var(--color-ink)] hover:underline"
                    onClick={() => void handleCopy(card.text, card.label, setCopied)}
                    type="button"
                  >
                    {copied === card.label ? 'Copied' : 'Copy'}
                  </button>
                </div>
                <CaptionCard label={card.label} text={card.text} tone={card.tone} />
              </div>
            ))
          : Array.from({ length: 4 }, (_, index) => (
              <div className="rounded-xl border border-[var(--color-line)] bg-white p-6" key={index}>
                <div className="h-4 w-24 rounded bg-[var(--color-surface-soft)]" />
                <div className="mt-5 space-y-3">
                  <div className="h-4 w-full rounded bg-[var(--color-surface-soft)]" />
                  <div className="h-4 w-full rounded bg-[var(--color-surface-soft)]" />
                  <div className="h-4 w-2/3 rounded bg-[var(--color-surface-soft)]" />
                </div>
              </div>
            ))}
      </section>
    </div>
  );
}

async function handleCopy(
  value: string,
  label: string,
  setCopied: (value: string | null) => void
) {
  await navigator.clipboard.writeText(value);
  setCopied(label);
  window.setTimeout(() => setCopied(null), 1400);
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}
