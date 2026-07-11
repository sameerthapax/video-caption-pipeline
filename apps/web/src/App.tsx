import { useContext } from 'react';
import {
  House,
  SignOut,
  UploadSimple,
  UserCircle,
} from '@phosphor-icons/react';
import { NavLink, Outlet, Route, Routes } from 'react-router-dom';
import { AuthContext } from './auth';
import { AuthGate } from './components/AuthGate';
import { DashboardPage } from './pages/DashboardPage';
import { JobStatusPage } from './pages/JobStatusPage';
import { NotFoundPage } from './pages/NotFoundPage';
import { ProfilePage } from './pages/ProfilePage';
import { ResultPage } from './pages/ResultPage';
import { UploadPage } from './pages/UploadPage';

export default function App() {
  const { isReady, user } = useContext(AuthContext);

  if (!isReady) {
    return (
      <main className="min-h-[100dvh] bg-[var(--color-canvas)] px-4 py-10 text-[var(--color-ink)] md:px-8">
        <div className="mx-auto max-w-6xl animate-fade-in">
          <div className="grid gap-6 md:grid-cols-[1.4fr_0.9fr]">
            <section className="rounded-xl border border-[var(--color-line)] bg-white p-8">
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--color-muted)]">
                Session
              </p>
              <h1 className="mt-4 max-w-2xl text-4xl font-semibold tracking-[-0.04em] text-balance md:text-6xl">
                Checking your workspace.
              </h1>
              <div className="mt-8 grid gap-3">
                <div className="h-4 w-40 rounded bg-[var(--color-surface-soft)]" />
                <div className="h-4 w-full rounded bg-[var(--color-surface-soft)]" />
                <div className="h-4 w-3/4 rounded bg-[var(--color-surface-soft)]" />
              </div>
            </section>
            <div className="rounded-xl border border-[var(--color-line)] bg-[var(--color-surface)] p-8">
              <div className="h-full min-h-64 rounded-lg bg-[var(--color-surface-soft)]" />
            </div>
          </div>
        </div>
      </main>
    );
  }

  if (!user) {
    return <AuthGate />;
  }

  return (
    <Routes>
      <Route element={<AppLayout />} path="/">
        <Route element={<DashboardPage />} index />
        <Route element={<UploadPage />} path="upload" />
        <Route element={<JobStatusPage />} path="jobs/:jobId" />
        <Route element={<ResultPage />} path="jobs/:jobId/result" />
        <Route element={<ProfilePage />} path="profile" />
        <Route element={<NotFoundPage />} path="*" />
      </Route>
    </Routes>
  );
}

function AppLayout() {
  const { logout, user } = useContext(AuthContext);

  if (!user) {
    return null;
  }

  return (
    <div className="min-h-[100dvh] bg-[var(--color-canvas)] text-[var(--color-ink)]">
      <a
        className="sr-only left-4 top-4 z-50 rounded-md bg-[var(--color-ink)] px-4 py-2 text-sm text-white focus:not-sr-only focus:fixed"
        href="#main-content"
      >
        Skip to content
      </a>
      <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
        <div className="absolute left-[-10%] top-10 h-72 w-72 rounded-full bg-[var(--color-accent-fog)] blur-3xl" />
        <div className="absolute bottom-0 right-[-8%] h-96 w-96 rounded-full bg-[var(--color-blue-fog)] blur-3xl" />
      </div>
      <header className="px-4 py-5 md:px-8">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 rounded-xl border border-[var(--color-line)] bg-[rgba(255,255,255,0.84)] px-4 py-4 backdrop-blur md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--color-muted)]">
              Video caption workspace
            </p>
            <h1 className="mt-2 text-xl font-semibold tracking-[-0.03em] text-[var(--color-ink)]">
              Assistive caption drafting for recorded video
            </h1>
          </div>
          <div className="flex flex-col gap-3 md:items-end">
            <nav aria-label="Primary" className="flex flex-wrap gap-2">
              <AppNavLink icon={House} label="Dashboard" to="/" />
              <AppNavLink icon={UploadSimple} label="Upload" to="/upload" />
              <AppNavLink icon={UserCircle} label="Profile" to="/profile" />
            </nav>
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex min-h-10 items-center rounded-md border border-[var(--color-line)] bg-white px-3 text-sm text-[var(--color-muted)]">
                {user.email ?? user.id}
              </span>
              <button
                className="inline-flex min-h-10 items-center gap-2 rounded-md bg-[var(--color-ink)] px-4 text-sm font-medium text-white transition duration-200 ease-[cubic-bezier(0.16,1,0.3,1)] hover:bg-[#2f3437] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-ink)] active:scale-[0.98]"
                onClick={() => void logout()}
                type="button"
              >
                <SignOut size={16} weight="bold" />
                Log out
              </button>
            </div>
          </div>
        </div>
      </header>
      <main className="px-4 pb-16 md:px-8" id="main-content">
        <div className="mx-auto max-w-7xl">
          <Outlet />
        </div>
      </main>
    </div>
  );
}

type AppNavLinkProps = {
  icon: typeof House;
  label: string;
  to: string;
};

function AppNavLink({ icon: Icon, label, to }: AppNavLinkProps) {
  return (
    <NavLink
      className={({ isActive }) =>
        [
          'inline-flex min-h-10 items-center gap-2 rounded-md border px-3 text-sm transition duration-200 ease-[cubic-bezier(0.16,1,0.3,1)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-ink)] active:scale-[0.98]',
          isActive
            ? 'border-[var(--color-ink)] bg-[var(--color-ink)] text-white'
            : 'border-[var(--color-line)] bg-white text-[var(--color-muted)] hover:border-[var(--color-ink)] hover:text-[var(--color-ink)]',
        ].join(' ')
      }
      end={to === '/'}
      to={to}
    >
      <Icon size={16} weight="fill" />
      {label}
    </NavLink>
  );
}
