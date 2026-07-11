import type { PropsWithChildren } from 'react';
import { createContext, useEffect, useRef, useState } from 'react';
import type { AuthUser } from './api';
import { getSession, login, logout, signup } from './api';

const SESSION_TIMEOUT_MS = 30 * 60 * 1000;
const ACTIVITY_EVENTS = ['pointerdown', 'keydown', 'scroll', 'focus'] as const;
export const AUTH_DISABLED = resolveAuthDisabled();
const GUEST_USER: AuthUser = { id: 'guest', email: null };

type AuthContextValue = {
  isReady: boolean;
  user: AuthUser | null;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

export const AuthContext = createContext<AuthContextValue>({
  isReady: false,
  user: null,
  login: async () => undefined,
  signup: async () => undefined,
  logout: async () => undefined
});

export function AuthProvider({ children }: PropsWithChildren) {
  const [user, setUser] = useState<AuthUser | null>(AUTH_DISABLED ? GUEST_USER : null);
  const [isReady, setIsReady] = useState(AUTH_DISABLED);
  const timerRef = useRef<number | null>(null);

  function clearInactivityTimer() {
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }

  function resetInactivityTimer(nextUser: AuthUser | null) {
    clearInactivityTimer();
    if (!nextUser) {
      return;
    }

    timerRef.current = window.setTimeout(() => {
      void handleLogout();
    }, SESSION_TIMEOUT_MS);
  }

  async function hydrateSession() {
    if (AUTH_DISABLED) {
      setUser(GUEST_USER);
      setIsReady(true);
      return;
    }
    try {
      const nextUser = await getSession();
      setUser(nextUser);
      resetInactivityTimer(nextUser);
    } catch {
      setUser(null);
      clearInactivityTimer();
    } finally {
      setIsReady(true);
    }
  }

  async function handleLogin(email: string, password: string) {
    if (AUTH_DISABLED) {
      setUser(GUEST_USER);
      setIsReady(true);
      return;
    }
    const nextUser = await login(email, password);
    setUser(nextUser);
    resetInactivityTimer(nextUser);
  }

  async function handleSignup(email: string, password: string) {
    if (AUTH_DISABLED) {
      setUser(GUEST_USER);
      setIsReady(true);
      return;
    }
    const nextUser = await signup(email, password);
    setUser(nextUser);
    resetInactivityTimer(nextUser);
  }

  async function handleLogout() {
    if (AUTH_DISABLED) {
      return;
    }
    await logout();
    setUser(null);
    clearInactivityTimer();
  }

  useEffect(() => {
    void hydrateSession();
  }, []);

  useEffect(() => {
    function handleActivity() {
      if (!user) {
        return;
      }
      resetInactivityTimer(user);
    }

    for (const eventName of ACTIVITY_EVENTS) {
      window.addEventListener(eventName, handleActivity, { passive: true });
    }

    return () => {
      clearInactivityTimer();
      for (const eventName of ACTIVITY_EVENTS) {
        window.removeEventListener(eventName, handleActivity);
      }
    };
  }, [user]);

  return (
    <AuthContext.Provider
      value={{
        isReady,
        user,
        login: handleLogin,
        signup: handleSignup,
        logout: handleLogout
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

function resolveAuthDisabled(): boolean {
  const configuredValue = import.meta.env.VITE_DISABLE_AUTH?.trim().toLowerCase();
  if (configuredValue) {
    return configuredValue === 'true';
  }

  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname;
    return hostname !== 'localhost' && hostname !== '127.0.0.1';
  }

  return false;
}
