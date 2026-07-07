import { useContext, useState } from 'react';
import type { FormEvent } from 'react';
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
    <main className="auth-shell">
      <section className="auth-hero">
        <div className="eyebrow">Backend Auth</div>
        <h1>Secure upload access for caption jobs.</h1>
        <p className="lede">
          Sign in before uploading videos. The browser only talks to your API, and your API owns the
          Supabase session plus per-user job access.
        </p>
      </section>

      <section className="auth-card panel">
        <div className="panel-header">
          <div>
            <div className="eyebrow">{mode === 'login' ? 'Login' : 'Create account'}</div>
            <h2>{mode === 'login' ? 'Access your workspace' : 'Start a new account'}</h2>
          </div>
          {!isReady ? <span className="status-pill">Checking session</span> : null}
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          <label className="field">
            <span>Email</span>
            <input
              autoComplete="email"
              className="text-input"
              onChange={(event) => setEmail(event.target.value)}
              required
              type="email"
              value={email}
            />
          </label>

          <label className="field">
            <span>Password</span>
            <input
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              className="text-input"
              minLength={6}
              onChange={(event) => setPassword(event.target.value)}
              required
              type="password"
              value={password}
            />
          </label>

          {error ? <p className="error">{error}</p> : null}
          {message ? <p className="success">{message}</p> : null}

          <div className="auth-actions">
            <button className="primary-button" disabled={isSubmitting || !isReady} type="submit">
              {isSubmitting ? 'Working...' : mode === 'login' ? 'Log in' : 'Create account'}
            </button>
            <button
              className="secondary-button"
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
    </main>
  );
}
