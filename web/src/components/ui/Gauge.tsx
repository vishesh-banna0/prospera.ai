"use client";

import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/cn";

/**
 * THE SIGNATURE (DESIGN.md §5).
 *
 * One calibrated instrument for every bounded machine reading — a company score
 * (0–100), a probability (0–1), a confidence (0–1), a signal strength. It pairs
 * a digital readout with an analog graduated track, like a multimeter, so "how
 * strong / how sure" reads identically everywhere in the app.
 *
 * The fill is the only place the gauge takes a data color. Confidence is `hold`
 * (slate) because confidence is not directional — you can be very sure of a Sell.
 */

export type GaugeTone = "up" | "down" | "hold";

const toneVar: Record<GaugeTone, string> = {
  up: "rgb(var(--up))",
  down: "rgb(var(--down))",
  hold: "rgb(var(--hold))",
};

export interface GaugeProps {
  /** The reading. */
  value: number;
  /** Scale bounds. Defaults 0–100 (scores); pass 0–1 for probabilities. */
  min?: number;
  max?: number;
  tone?: GaugeTone;
  /** Formatted reading for the digital display, e.g. "72" or "0.72". */
  readout: string;
  /** Small eyebrow label above the instrument. */
  label?: string;
  /** Low/high captions under the track ends. */
  caption?: [string, string];
  majorTicks?: number;
  minorPerMajor?: number;
  ariaLabel: string;
  className?: string;
}

export function Gauge({
  value,
  min = 0,
  max = 100,
  tone = "hold",
  readout,
  label,
  caption,
  majorTicks = 4,
  minorPerMajor = 5,
  ariaLabel,
  className,
}: GaugeProps) {
  const frac = clamp((value - min) / (max - min || 1), 0, 1);

  // Sweep the level from 0 to its reading once on mount. Under
  // prefers-reduced-motion the global CSS neutralizes the transition to instant.
  const [level, setLevel] = useState(0);
  const mounted = useRef(false);
  useEffect(() => {
    if (mounted.current) return;
    mounted.current = true;
    const id = requestAnimationFrame(() => setLevel(frac));
    return () => cancelAnimationFrame(id);
  }, [frac]);

  const color = toneVar[tone];
  const totalTicks = majorTicks * minorPerMajor;
  const pct = `${level * 100}%`;

  return (
    <div className={cn("select-none", className)}>
      {(label || readout) && (
        <div className="mb-1.5 flex items-baseline justify-between gap-3">
          {label ? <span className="eyebrow">{label}</span> : <span />}
          <span
            className="font-mono text-lg font-medium leading-none tnum"
            style={{ color }}
          >
            {readout}
          </span>
        </div>
      )}

      <div
        className="relative h-9"
        role="meter"
        aria-valuenow={value}
        aria-valuemin={min}
        aria-valuemax={max}
        aria-label={ariaLabel}
      >
        {/* analog track: baseline + graduated ticks (static) */}
        <svg
          className="absolute inset-0 h-full w-full"
          viewBox="0 0 1000 36"
          preserveAspectRatio="none"
          aria-hidden
        >
          <line x1="0" y1="30" x2="1000" y2="30" stroke="rgb(var(--line-2))" strokeWidth="1" vectorEffect="non-scaling-stroke" />
          {Array.from({ length: totalTicks + 1 }, (_, i) => {
            const x = (i / totalTicks) * 1000;
            const major = i % minorPerMajor === 0;
            return (
              <line
                key={i}
                x1={x}
                x2={x}
                y1={major ? 18 : 24}
                y2={30}
                stroke={major ? "rgb(var(--fg-mute))" : "rgb(var(--line-2))"}
                strokeWidth="1"
                vectorEffect="non-scaling-stroke"
              />
            );
          })}
        </svg>

        {/* fill up to the level */}
        <div
          className="absolute bottom-[6px] left-0 top-0 border-r-2 transition-[width] duration-500 ease-out"
          style={{
            width: pct,
            borderColor: color,
            background: `linear-gradient(to top, color-mix(in srgb, ${color} 18%, transparent), transparent)`,
          }}
        />

        {/* level pointer */}
        <div
          className="absolute top-0 h-0 w-0 -translate-x-1/2 transition-[left] duration-500 ease-out"
          style={{
            left: pct,
            borderLeft: "4px solid transparent",
            borderRight: "4px solid transparent",
            borderTop: `5px solid ${color}`,
          }}
          aria-hidden
        />
      </div>

      {caption && (
        <div className="mt-1 flex justify-between font-mono text-[0.625rem] uppercase tracking-wider text-fg-mute">
          <span>{caption[0]}</span>
          <span>{caption[1]}</span>
        </div>
      )}
    </div>
  );
}

function clamp(n: number, lo: number, hi: number) {
  return Math.min(hi, Math.max(lo, n));
}
