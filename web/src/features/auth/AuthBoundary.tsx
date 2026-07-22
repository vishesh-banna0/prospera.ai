"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";
import { AppShell } from "@/components/shell/AppShell";
import { useAuth } from "./AuthProvider";

const AUTH_PATHS = new Set(["/login", "/register"]);

/** Gates the app behind login. Unauthenticated users are sent to /login; the
 *  login/register pages render bare (no app chrome), and every other page renders
 *  inside the normal AppShell only when signed in. */
export function AuthBoundary({ children }: { children: ReactNode }) {
  const { ready, isAuthed } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const isAuthPage = AUTH_PATHS.has(pathname);

  useEffect(() => {
    if (!ready) return;
    if (!isAuthed && !isAuthPage) {
      router.replace("/login");
    } else if (isAuthed && isAuthPage) {
      router.replace("/");
    }
  }, [ready, isAuthed, isAuthPage, router]);

  // Until we've read the stored token (or while a redirect is pending), render
  // nothing rather than flashing the wrong screen.
  if (!ready) return null;
  if (isAuthPage) return <>{children}</>;
  if (!isAuthed) return null;
  return <AppShell>{children}</AppShell>;
}
