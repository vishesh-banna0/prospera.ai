"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { clearToken, getToken, setToken } from "./token";

const USERNAME_KEY = "prospera_username";

interface AuthState {
  /** True once we've read the stored token on the client (avoids an SSR flash). */
  ready: boolean;
  isAuthed: boolean;
  username: string | null;
  signIn: (token: string, username: string) => void;
  signOut: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

/** Holds the login state (token + username) in React so the UI reacts to sign
 *  in / out, mirroring it into localStorage so it survives a reload. */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const [token, setTokenState] = useState<string | null>(null);
  const [username, setUsername] = useState<string | null>(null);

  useEffect(() => {
    setTokenState(getToken());
    try {
      setUsername(window.localStorage.getItem(USERNAME_KEY));
    } catch {
      /* ignore */
    }
    setReady(true);
  }, []);

  const signIn = useCallback((newToken: string, newUsername: string) => {
    setToken(newToken);
    try {
      window.localStorage.setItem(USERNAME_KEY, newUsername);
    } catch {
      /* ignore */
    }
    setTokenState(newToken);
    setUsername(newUsername);
  }, []);

  const signOut = useCallback(() => {
    clearToken();
    try {
      window.localStorage.removeItem(USERNAME_KEY);
    } catch {
      /* ignore */
    }
    setTokenState(null);
    setUsername(null);
  }, []);

  return (
    <AuthContext.Provider value={{ ready, isAuthed: token !== null, username, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
