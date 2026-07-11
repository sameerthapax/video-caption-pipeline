import { useEffect, useState, type ReactNode } from 'react';
import { EnvelopeSimple, IdentificationCard } from '@phosphor-icons/react';
import type { AuthProfileResponse, JobListItemResponse } from '@shared-types';
import { getProfile, listJobs } from '../api';
import { BackButton } from '../components/BackButton';
import { JobStatusBadge } from '../components/JobStatusBadge';

export function ProfilePage() {
  const [profile, setProfile] = useState<AuthProfileResponse | null>(null);
  const [jobs, setJobs] = useState<JobListItemResponse[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [nextProfile, nextJobs] = await Promise.all([getProfile(), listJobs()]);
        if (!cancelled) {
          setProfile(nextProfile);
          setJobs(nextJobs);
          setError(null);
        }
      } catch (nextError) {
        if (!cancelled) {
          setError(nextError instanceof Error ? nextError.message : 'Could not load profile.');
        }
      }
    }

    void load();

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <BackButton fallbackTo="/" />
      </div>

      {error ? (
        <div className="rounded-xl border border-[var(--color-line)] bg-[var(--color-tag-red-bg)] px-5 py-4 text-sm text-[var(--color-tag-red-text)]">
          {error}
        </div>
      ) : null}

      <section className="grid gap-6 md:grid-cols-[0.9fr_1.1fr]">
        <article className="animate-fade-in rounded-xl border border-[var(--color-line)] bg-white p-8">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--color-muted)]">
            Profile
          </p>
          <h2 className="mt-4 text-3xl font-semibold tracking-[-0.05em] md:text-5xl">
            Account and workload summary
          </h2>

          <div className="mt-8 space-y-4">
            <InfoRow
              icon={<EnvelopeSimple size={18} weight="fill" />}
              label="Email"
              value={profile?.user.email ?? 'No email'}
            />
            <InfoRow
              icon={<IdentificationCard size={18} weight="fill" />}
              label="User ID"
              value={profile?.user.id ?? 'Loading'}
            />
          </div>
        </article>

        <article className="animate-fade-in rounded-xl border border-[var(--color-line)] bg-[var(--color-surface)] p-8">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--color-muted)]">
            Totals
          </p>
          <div className="mt-6 grid gap-4 md:grid-cols-2">
            <SummaryCell label="All jobs" value={String(profile?.totalJobs ?? 0)} />
            <SummaryCell label="Completed" value={String(profile?.completedJobs ?? 0)} />
            <SummaryCell label="Active" value={String(profile?.activeJobs ?? 0)} />
            <SummaryCell label="Failed" value={String(profile?.failedJobs ?? 0)} />
          </div>
        </article>
      </section>

      <section className="animate-fade-in rounded-xl border border-[var(--color-line)] bg-white p-6 md:p-8">
        <div className="flex items-end justify-between gap-4 border-b border-[var(--color-line)] pb-5">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--color-muted)]">
              Recent uploads
            </p>
            <h3 className="mt-3 text-2xl font-semibold tracking-[-0.04em]">Latest job activity</h3>
          </div>
        </div>
        {jobs.length === 0 ? (
          <p className="mt-6 text-sm text-[var(--color-muted)]">No uploads yet.</p>
        ) : (
          <ul className="mt-4 divide-y divide-[var(--color-line)]">
            {jobs.slice(0, 6).map((job) => (
              <li className="grid gap-3 py-4 md:grid-cols-[1fr_auto_auto]" key={job.id}>
                <div>
                  <p className="font-medium text-[var(--color-ink)]">{job.originalFilename}</p>
                  <p className="mt-1 text-sm text-[var(--color-muted)]">{formatDate(job.createdAt)}</p>
                </div>
                <div className="self-center">
                  <JobStatusBadge status={job.status} />
                </div>
                <p className="self-center font-mono text-sm text-[var(--color-muted)]">{job.progress}%</p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function InfoRow({
  icon,
  label,
  value,
}: {
  icon: ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-start gap-4 rounded-lg border border-[var(--color-line)] bg-[var(--color-surface)] p-4">
      <div className="rounded-lg bg-white p-3 text-[var(--color-ink)]">{icon}</div>
      <div className="min-w-0">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--color-muted)]">
          {label}
        </p>
        <p className="mt-2 break-all text-sm text-[var(--color-ink)]">{value}</p>
      </div>
    </div>
  );
}

function SummaryCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-[var(--color-line)] bg-white p-5">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--color-muted)]">
        {label}
      </p>
      <p className="mt-4 font-mono text-3xl tracking-[-0.04em] text-[var(--color-ink)]">{value}</p>
    </div>
  );
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}
