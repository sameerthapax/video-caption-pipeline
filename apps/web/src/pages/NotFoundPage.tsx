import { Link } from 'react-router-dom';
import { BackButton } from '../components/BackButton';

export function NotFoundPage() {
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <BackButton fallbackTo="/" />
      </div>
      <section className="animate-fade-in rounded-xl border border-[var(--color-line)] bg-white p-8 md:p-10">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--color-muted)]">
          Page not found
        </p>
        <h2 className="mt-4 text-4xl font-semibold tracking-[-0.05em] md:text-5xl">
          This route does not exist in the workspace.
        </h2>
        <p className="mt-5 max-w-2xl text-base leading-8 text-[var(--color-muted)]">
          Return to the dashboard or start a new upload from the main workspace.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link
            className="inline-flex min-h-12 items-center rounded-md bg-[var(--color-ink)] px-5 text-sm font-medium text-white transition duration-200 ease-[cubic-bezier(0.16,1,0.3,1)] hover:bg-[#2f3437] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-ink)] active:scale-[0.98]"
            to="/"
          >
            Go to dashboard
          </Link>
          <Link
            className="inline-flex min-h-12 items-center rounded-md border border-[var(--color-line)] bg-[var(--color-surface)] px-5 text-sm font-medium text-[var(--color-ink)] transition duration-200 ease-[cubic-bezier(0.16,1,0.3,1)] hover:border-[var(--color-ink)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-ink)] active:scale-[0.98]"
            to="/upload"
          >
            Start upload
          </Link>
        </div>
      </section>
    </div>
  );
}
