import { useContext, useState } from 'react';
import type { FormEvent } from 'react';
import { Key, UploadSimple } from '@phosphor-icons/react';
import { AuthContext } from '../auth';

export function AuthGate() {
  const { isReady, login, signup } = useContext(AuthContext);
  const [mode, setMode] = useState<'login' | 'signup'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    setMessage(null);

    try {
      if (mode === 'login') {
        await login(email, password);
        setMessage('Signed in.');
      } else {
        await signup(email, password);
        setMessage('Account created and signed in.');
      }
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : 'Authentication failed.');
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="min-h-[100dvh] bg-[var(--color-canvas)] px-4 py-8 text-[var(--color-ink)] md:px-8 md:py-10">
      <div className="mx-auto grid max-w-7xl gap-6 md:grid-cols-[1.35fr_0.95fr]">
        <section className="animate-fade-in rounded-xl border border-[var(--color-line)] bg-white p-8 md:p-12">
          <span className="inline-flex items-center rounded-full bg-[var(--color-tag-blue-bg)] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--color-tag-blue-text)]">
            Assistive workflow
          </span>
          <h1 className="mt-6 max-w-3xl text-4xl font-semibold tracking-[-0.05em] text-balance md:text-6xl">
            Draft grounded captions from video with a calm, readable workspace.
          </h1>
          <p className="mt-6 max-w-2xl text-base leading-8 text-[var(--color-muted)]">
            Upload footage, monitor extraction, and review caption variants built to support clearer
            access to recorded visual content.
          </p>
          <div className="mt-10 grid gap-4 md:grid-cols-[1.3fr_0.9fr]">
            <article className="rounded-xl border border-[var(--color-line)] bg-[var(--color-surface)] p-6">
              <UploadSimple className="text-[var(--color-ink)]" size={22} weight="fill" />
              <h2 className="mt-5 text-lg font-semibold tracking-[-0.03em]">Direct upload</h2>
              <p className="mt-3 text-sm leading-7 text-[var(--color-muted)]">
                The browser sends the file to storage, then the API verifies it and queues the
                worker.
              </p>
            </article>
            <article className="rounded-xl border border-[var(--color-line)] bg-[var(--color-surface)] p-6">
              <Key className="text-[var(--color-ink)]" size={22} weight="fill" />
              <h2 className="mt-5 text-lg font-semibold tracking-[-0.03em]">Protected access</h2>
              <p className="mt-3 text-sm leading-7 text-[var(--color-muted)]">
                Authentication and CSRF protection keep each user scoped to their own jobs.
              </p>
            </article>
          </div>
        </section>

        <section className="animate-fade-in rounded-xl border border-[var(--color-line)] bg-[var(--color-surface)] p-8 md:p-10">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--color-muted)]">
                {mode === 'login' ? 'Sign in' : 'Create account'}
              </p>
              <h2 className="mt-3 text-2xl font-semibold tracking-[-0.04em]">
                {mode === 'login' ? 'Open your workspace' : 'Set up access'}
              </h2>
            </div>
            {!isReady ? (
              <span className="rounded-full bg-[var(--color-tag-yellow-bg)] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--color-tag-yellow-text)]">
                Checking
              </span>
            ) : null}
          </div>

          <form className="mt-8 space-y-5" onSubmit={handleSubmit}>
            <div className="grid gap-2">
              <label className="text-sm font-medium text-[var(--color-ink)]" htmlFor="email">
                Email
              </label>
              <input
                autoComplete="email"
                className="min-h-12 rounded-md border border-[var(--color-line)] bg-white px-4 text-[var(--color-ink)] outline-none transition focus:border-[var(--color-ink)]"
                id="email"
                onChange={(event) => setEmail(event.target.value)}
                required
                type="email"
                value={email}
              />
            </div>

            <div className="grid gap-2">
              <label className="text-sm font-medium text-[var(--color-ink)]" htmlFor="password">
                Password
              </label>
              <input
                autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                className="min-h-12 rounded-md border border-[var(--color-line)] bg-white px-4 text-[var(--color-ink)] outline-none transition focus:border-[var(--color-ink)]"
                id="password"
                minLength={6}
                onChange={(event) => setPassword(event.target.value)}
                required
                type="password"
                value={password}
              />
              <p className="text-sm text-[var(--color-muted)]">Use at least 6 characters.</p>
            </div>

            {error ? (
              <p className="rounded-md bg-[var(--color-tag-red-bg)] px-4 py-3 text-sm text-[var(--color-tag-red-text)]">
                {error}
              </p>
            ) : null}
            {message ? (
              <p className="rounded-md bg-[var(--color-tag-green-bg)] px-4 py-3 text-sm text-[var(--color-tag-green-text)]">
                {message}
              </p>
            ) : null}

            <div className="flex flex-wrap gap-3 pt-2">
              <button
                className="inline-flex min-h-12 items-center justify-center rounded-md bg-[var(--color-ink)] px-5 text-sm font-medium text-white transition duration-200 ease-[cubic-bezier(0.16,1,0.3,1)] hover:bg-[#2f3437] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-ink)] active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-60"
                disabled={isSubmitting || !isReady}
                type="submit"
              >
                {isSubmitting ? 'Working...' : mode === 'login' ? 'Log in' : 'Create account'}
              </button>
              <button
                className="inline-flex min-h-12 items-center justify-center rounded-md border border-[var(--color-line)] bg-white px-5 text-sm font-medium text-[var(--color-muted)] transition duration-200 ease-[cubic-bezier(0.16,1,0.3,1)] hover:border-[var(--color-ink)] hover:text-[var(--color-ink)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-ink)] active:scale-[0.98]"
                onClick={() => {
                  setMode((currentMode) => (currentMode === 'login' ? 'signup' : 'login'));
                  setError(null);
                  setMessage(null);
                }}
                type="button"
              >
                {mode === 'login' ? 'Need an account?' : 'Already have an account?'}
              </button>
            </div>
          </form>
        </section>
      </div>
    </main>
  );
}
