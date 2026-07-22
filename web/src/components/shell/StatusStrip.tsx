"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useHealth } from "@/lib/useHealth";
import { useAuth } from "@/features/auth/AuthProvider";
import { cn } from "@/lib/cn";

/**
 * The instrument's status bar. Health, clock, base currency, and — permanently —
 * the "not investment advice" plate. Machine opinion is always labelled, so the
 * plate is part of the frame, never a footer that scrolls away.
 */
export function StatusStrip() {
  const health = useHealth();

  const state: "ok" | "down" | "checking" = health.isLoading
    ? "checking"
    : health.isError
      ? "down"
      : "ok";

  return (
    <header className="flex h-strip shrink-0 items-center gap-4 border-b border-line bg-panel px-3">
      <Wordmark />

      <div className="mx-1 h-4 w-px bg-line-2" aria-hidden />

      <HealthPip state={state} />

      <MarketClock />

      <div className="ml-auto flex items-center gap-3">
        <span className="font-mono text-2xs text-fg-dim tnum">₹ INR</span>
        <AdvicePlate />
        <Account />
      </div>
    </header>
  );
}

function Account() {
  const { username, signOut } = useAuth();
  const router = useRouter();

  function handleSignOut() {
    signOut();
    router.replace("/login");
  }

  return (
    <div className="flex items-center gap-2">
      {username && (
        <span className="hidden font-mono text-2xs text-fg-dim sm:inline" title="Signed in">
          {username}
        </span>
      )}
      <button
        type="button"
        onClick={handleSignOut}
        className="rounded-sm border border-line-2 px-2 py-1 font-mono text-[0.625rem] uppercase tracking-wider text-fg-mute hover:border-fg-mute hover:text-fg"
      >
        Sign out
      </button>
    </div>
  );
}

function Wordmark() {
  return (
    <div className="flex items-baseline gap-2 pl-1">
      <span className="font-display text-sm font-bold tracking-[0.16em] text-fg">PROSPERA</span>
      <span className="eyebrow hidden sm:inline">· instrument</span>
    </div>
  );
}

function HealthPip({ state }: { state: "ok" | "down" | "checking" }) {
  const label =
    state === "ok" ? "live" : state === "down" ? "offline" : "checking";
  const dot =
    state === "ok" ? "bg-up" : state === "down" ? "bg-down" : "bg-fg-mute";
  return (
    <div className="flex items-center gap-1.5" title={`Backend ${label}`}>
      <span className={cn("h-1.5 w-1.5 rounded-full", dot)} aria-hidden />
      <span className="font-mono text-2xs uppercase tracking-wider text-fg-dim">{label}</span>
    </div>
  );
}

function MarketClock() {
  const [time, setTime] = useState<string | null>(null);
  useEffect(() => {
    const tick = () =>
      setTime(
        new Date().toLocaleTimeString("en-IN", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
          hour12: false,
          timeZone: "Asia/Kolkata",
        }),
      );
    tick();
    const id = window.setInterval(tick, 1000);
    return () => window.clearInterval(id);
  }, []);
  return (
    <div className="hidden items-baseline gap-1.5 md:flex">
      <span className="font-mono text-2xs uppercase tracking-wider text-fg-mute">IST</span>
      <span className="font-mono text-2xs text-fg-dim tnum">{time ?? "--:--:--"}</span>
    </div>
  );
}

function AdvicePlate() {
  return (
    <span
      className="rounded-sm border border-line-2 px-2 py-1 font-mono text-[0.625rem] uppercase tracking-[0.12em] text-fg-mute"
      title="Every figure here is simulated. Nothing in Prospera is investment advice."
    >
      Simulated — not advice
    </span>
  );
}
