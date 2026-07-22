"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { Input, Field } from "@/components/ui/Input";
import { ApiError } from "@/api/client";
import { useLogin, useRegister } from "../hooks";

/** The login and register screens are the same form with different copy — one
 *  component, a `mode` switch. On success the app unlocks and routes home. */
export function AuthForm({ mode }: { mode: "login" | "register" }) {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const login = useLogin();
  const register = useRegister();
  const mutation = mode === "login" ? login : register;

  const valid = username.trim() !== "" && password !== "";

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!valid) return;
    mutation.mutate(
      { username: username.trim(), password },
      { onSuccess: () => router.replace("/") },
    );
  }

  const isRegister = mode === "register";

  return (
    <div className="flex min-h-dvh items-center justify-center px-4 py-10">
      <div className="w-full max-w-sm">
        <div className="mb-6 text-center">
          <p className="font-display text-lg font-bold tracking-tight text-fg">PROSPERA</p>
          <p className="mt-1 font-mono text-[0.625rem] uppercase tracking-widest text-fg-mute">
            Instrument · Paper trading
          </p>
        </div>

        <section className="rounded border border-line bg-panel p-5">
          <h1 className="font-display text-base font-bold text-fg">
            {isRegister ? "Create account" : "Sign in"}
          </h1>
          <p className="mt-1 text-2xs text-fg-dim">
            {isRegister
              ? "Pick a username and password to start paper trading."
              : "Welcome back. Enter your credentials to continue."}
          </p>

          <form onSubmit={submit} className="mt-4 flex flex-col gap-3">
            <Field
              label="Username"
              htmlFor="auth-username"
              hint={isRegister ? "At least 3 characters" : undefined}
            >
              <Input
                id="auth-username"
                autoFocus
                autoComplete="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                invalid={mutation.isError}
              />
            </Field>
            <Field
              label="Password"
              htmlFor="auth-password"
              hint={isRegister ? "At least 8 characters" : undefined}
            >
              <Input
                id="auth-password"
                type="password"
                autoComplete={isRegister ? "new-password" : "current-password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                invalid={mutation.isError}
              />
            </Field>
            <Button
              type="submit"
              variant="primary"
              loading={mutation.isPending}
              disabled={!valid}
            >
              {isRegister ? "Create account" : "Sign in"}
            </Button>
          </form>

          {mutation.isError && (
            <p className="mt-2 break-words font-mono text-2xs text-down">
              {(mutation.error as ApiError).message}
            </p>
          )}
        </section>

        <p className="mt-4 text-center text-2xs text-fg-mute">
          {isRegister ? (
            <>
              Have an account?{" "}
              <Link href="/login" className="text-fg-dim underline-offset-2 hover:text-fg hover:underline">
                Sign in
              </Link>
            </>
          ) : (
            <>
              No account?{" "}
              <Link href="/register" className="text-fg-dim underline-offset-2 hover:text-fg hover:underline">
                Create one
              </Link>
            </>
          )}
        </p>
      </div>
    </div>
  );
}
