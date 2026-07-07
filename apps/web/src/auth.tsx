import type { PropsWithChildren } from 'react';
import { createContext, useEffect, useRef, useState } from 'react';
import type { AuthUser } from './api';
import { getSession, login, logout, signup } from './api';

const SESSION_TIMEOUT_MS = 30 * 60 * 1000;
const ACTIVITY_EVENTS = ['pointerdown', 'keydown', 'scroll', 'focus'] as const;

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
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isReady, setIsReady] = useState(false);
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
    const nextUser = await login(email, password);
    setUser(nextUser);
    resetInactivityTimer(nextUser);
  }

  async function handleSignup(email: string, password: string) {
    const nextUser = await signup(email, password);
    setUser(nextUser);
    resetInactivityTimer(nextUser);
  }

  async function handleLogout() {
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
