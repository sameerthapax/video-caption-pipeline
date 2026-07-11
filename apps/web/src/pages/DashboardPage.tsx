import { useEffect, useMemo, useState, type ReactNode } from 'react';
import {
  ArrowRight,
  CheckCircle,
  ClockCounterClockwise,
  WarningCircle,
} from '@phosphor-icons/react';
import type { AuthProfileResponse, JobListItemResponse } from '@shared-types';
import { Link } from 'react-router-dom';
import { getProfile, listJobs } from '../api';
import { JobStatusBadge } from '../components/JobStatusBadge';

export function DashboardPage() {
  const [profile, setProfile] = useState<AuthProfileResponse | null>(null);
  const [jobs, setJobs] = useState<JobListItemResponse[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setIsLoading(true);
      setError(null);

      try {
        const [nextProfile, nextJobs] = await Promise.all([getProfile(), listJobs()]);
        if (cancelled) {
          return;
        }
        setProfile(nextProfile);
        setJobs(nextJobs);
      } catch (nextError) {
        if (!cancelled) {
          setError(nextError instanceof Error ? nextError.message : 'Could not load dashboard data.');
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void load();

    return () => {
      cancelled = true;
    };
  }, []);

  const latestCompletedJob = useMemo(
    () => jobs.find((job) => job.status === 'completed' && job.hasResult),
    [jobs]
  );

  return (
    <div className="space-y-6">
      <section className="grid gap-6 md:grid-cols-[1.2fr_0.8fr]">
        <article className="animate-fade-in rounded-xl border border-[var(--color-line)] bg-white p-8 md:p-10">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--color-muted)]">
            Dashboard
          </p>
          <h2 className="mt-4 max-w-3xl text-4xl font-semibold tracking-[-0.05em] text-balance md:text-6xl">
            Track uploads, worker progress, and caption results without losing context.
          </h2>
          <p className="mt-6 max-w-2xl text-base leading-8 text-[var(--color-muted)]">
            The workspace keeps each upload tied to its extraction status so caption review stays
            readable and predictable.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link
              className="inline-flex min-h-12 items-center gap-2 rounded-md bg-[var(--color-ink)] px-5 text-sm font-medium text-white transition duration-200 ease-[cubic-bezier(0.16,1,0.3,1)] hover:bg-[#2f3437] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-ink)] active:scale-[0.98]"
              to="/upload"
            >
              Start new upload
              <ArrowRight size={16} weight="bold" />
            </Link>
            {latestCompletedJob ? (
              <Link
                className="inline-flex min-h-12 items-center rounded-md border border-[var(--color-line)] bg-[var(--color-surface)] px-5 text-sm font-medium text-[var(--color-ink)] transition duration-200 ease-[cubic-bezier(0.16,1,0.3,1)] hover:border-[var(--color-ink)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-ink)] active:scale-[0.98]"
                to={`/jobs/${latestCompletedJob.id}/result`}
              >
                Open latest result
              </Link>
            ) : null}
          </div>
        </article>

        <aside className="animate-fade-in rounded-xl border border-[var(--color-line)] bg-[var(--color-surface)] p-8">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--color-muted)]">
            Why this exists
          </p>
          <p className="mt-4 text-lg font-medium tracking-[-0.03em] text-[var(--color-ink)]">
            Support faster access to the visual meaning of recorded clips.
          </p>
          <p className="mt-4 text-sm leading-7 text-[var(--color-muted)]">
            The output set is designed to help teams draft clearer captions and context summaries for
            people who rely on accessible video descriptions.
          </p>
        </aside>
      </section>

      {error ? (
        <div className="rounded-xl border border-[var(--color-line)] bg-[var(--color-tag-red-bg)] px-5 py-4 text-sm text-[var(--color-tag-red-text)]">
          {error}
        </div>
      ) : null}

      <section className="grid gap-4 md:grid-cols-[1.1fr_0.9fr_0.9fr]">
        {isLoading ? (
          <>
            <MetricSkeleton />
            <MetricSkeleton />
            <MetricSkeleton />
          </>
        ) : (
          <>
            <MetricCard
              description="All uploads linked to your account"
              icon={<ClockCounterClockwise size={20} weight="fill" />}
              label="Total jobs"
              value={String(profile?.totalJobs ?? 0)}
            />
            <MetricCard
              description="Completed caption sets ready to review"
              icon={<CheckCircle size={20} weight="fill" />}
              label="Completed"
              value={String(profile?.completedJobs ?? 0)}
            />
            <MetricCard
              description="Uploads still moving through preprocessing or reasoning"
              icon={<WarningCircle size={20} weight="fill" />}
              label="Active now"
              value={String(profile?.activeJobs ?? 0)}
            />
          </>
        )}
      </section>

      <section className="grid gap-6 md:grid-cols-[1.25fr_0.75fr]">
        <article className="animate-fade-in rounded-xl border border-[var(--color-line)] bg-white p-6 md:p-8">
          <div className="flex items-end justify-between gap-4 border-b border-[var(--color-line)] pb-5">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--color-muted)]">
                Recent jobs
              </p>
              <h3 className="mt-3 text-2xl font-semibold tracking-[-0.04em]">Processing history</h3>
            </div>
            <Link className="text-sm text-[var(--color-muted)] underline-offset-4 hover:text-[var(--color-ink)] hover:underline" to="/upload">
              Upload another
            </Link>
          </div>

          <div className="mt-3">
            {isLoading ? (
              <div className="space-y-3">
                <JobRowSkeleton />
                <JobRowSkeleton />
                <JobRowSkeleton />
              </div>
            ) : jobs.length === 0 ? (
              <div className="rounded-lg bg-[var(--color-surface)] p-6">
                <p className="text-lg font-medium tracking-[-0.03em]">No uploads yet</p>
                <p className="mt-2 max-w-xl text-sm leading-7 text-[var(--color-muted)]">
                  Start with a short clip to create your first caption draft set and track it here.
                </p>
              </div>
            ) : (
              <ul className="divide-y divide-[var(--color-line)]">
                {jobs.map((job, index) => (
                  <li
                    className="animate-fade-in py-4"
                    key={job.id}
                    style={{ animationDelay: `${index * 80}ms` }}
                  >
                    <Link
                      className="grid gap-3 rounded-lg px-2 py-2 transition duration-200 ease-[cubic-bezier(0.16,1,0.3,1)] hover:bg-[var(--color-surface)] md:grid-cols-[1.1fr_0.7fr_0.5fr]"
                      to={job.hasResult ? `/jobs/${job.id}/result` : `/jobs/${job.id}`}
                    >
                      <div>
                        <p className="font-medium text-[var(--color-ink)]">{job.originalFilename}</p>
                        <p className="mt-1 text-sm text-[var(--color-muted)]">
                          {formatDate(job.createdAt)}
                        </p>
                      </div>
                      <div className="space-y-2">
                        <JobStatusBadge status={job.status} />
                        <p className="font-mono text-sm text-[var(--color-muted)]">{job.currentStep}</p>
                      </div>
                      <div className="self-center text-sm text-[var(--color-muted)] md:text-right">
                        {job.progress}%
                      </div>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </article>

        <aside className="grid gap-6">
          <article className="animate-fade-in rounded-xl border border-[var(--color-line)] bg-[var(--color-surface)] p-6">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--color-muted)]">
              Account summary
            </p>
            <dl className="mt-5 space-y-4">
              <div className="flex items-baseline justify-between gap-4 border-b border-[var(--color-line)] pb-3">
                <dt className="text-sm text-[var(--color-muted)]">Failed jobs</dt>
                <dd className="font-mono text-sm text-[var(--color-ink)]">{profile?.failedJobs ?? 0}</dd>
              </div>
              <div className="flex items-baseline justify-between gap-4 border-b border-[var(--color-line)] pb-3">
                <dt className="text-sm text-[var(--color-muted)]">Latest upload</dt>
                <dd className="text-right text-sm text-[var(--color-ink)]">
                  {profile?.latestJobAt ? formatDate(profile.latestJobAt) : 'No uploads yet'}
                </dd>
              </div>
              <div className="flex items-baseline justify-between gap-4">
                <dt className="text-sm text-[var(--color-muted)]">Review path</dt>
                <dd className="text-sm text-[var(--color-ink)]">Upload, inspect, export</dd>
              </div>
            </dl>
          </article>

          <article className="animate-fade-in rounded-xl border border-[var(--color-line)] bg-white p-6">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--color-muted)]">
              Working notes
            </p>
            <ul className="mt-5 space-y-3 text-sm leading-7 text-[var(--color-muted)]">
              <li>Use short, stable source clips while the pipeline is still evolving.</li>
              <li>Completed jobs open directly to the saved caption result page.</li>
              <li>Processing jobs stay live in the status route until the worker finishes.</li>
            </ul>
          </article>
        </aside>
      </section>
    </div>
  );
}

function MetricCard({
  description,
  icon,
  label,
  value,
}: {
  description: string;
  icon: ReactNode;
  label: string;
  value: string;
}) {
  return (
    <article className="animate-fade-in rounded-xl border border-[var(--color-line)] bg-white p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--color-muted)]">
            {label}
          </p>
          <p className="mt-4 font-mono text-4xl tracking-[-0.05em] text-[var(--color-ink)]">{value}</p>
        </div>
        <div className="rounded-lg bg-[var(--color-surface)] p-3 text-[var(--color-ink)]">{icon}</div>
      </div>
      <p className="mt-4 max-w-xs text-sm leading-7 text-[var(--color-muted)]">{description}</p>
    </article>
  );
}

function MetricSkeleton() {
  return (
    <article className="rounded-xl border border-[var(--color-line)] bg-white p-6">
      <div className="h-3 w-20 rounded bg-[var(--color-surface-soft)]" />
      <div className="mt-4 h-10 w-24 rounded bg-[var(--color-surface-soft)]" />
      <div className="mt-4 h-3 w-full rounded bg-[var(--color-surface-soft)]" />
    </article>
  );
}

function JobRowSkeleton() {
  return (
    <div className="grid gap-3 py-4 md:grid-cols-[1.1fr_0.7fr_0.5fr]">
      <div className="space-y-2">
        <div className="h-4 w-44 rounded bg-[var(--color-surface-soft)]" />
        <div className="h-3 w-32 rounded bg-[var(--color-surface-soft)]" />
      </div>
      <div className="space-y-2">
        <div className="h-6 w-24 rounded-full bg-[var(--color-surface-soft)]" />
        <div className="h-3 w-28 rounded bg-[var(--color-surface-soft)]" />
      </div>
      <div className="h-4 w-14 rounded bg-[var(--color-surface-soft)] md:justify-self-end" />
    </div>
  );
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}
