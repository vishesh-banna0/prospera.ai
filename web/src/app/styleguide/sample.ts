import type { EquityPoint } from "@/components/charts/EquityCurve";

/**
 * Deterministic SAMPLE series for demonstrating the chart component in the
 * styleguide only. Not random (so it's hydration-stable) and never shipped on a
 * product screen — product charts take real backtest data from the API.
 */
export function sampleEquityCurve(months = 30): EquityPoint[] {
  const monthly = 5000; // ₹5,000/mo SIP
  const start = new Date("2023-01-01T00:00:00Z");
  const points: EquityPoint[] = [];
  let value = 0;
  for (let i = 0; i < months; i++) {
    const invested = monthly * (i + 1);
    // A smooth, seeded drift + gentle wobble — no Math.random.
    const drift = 1 + i * 0.012;
    const wobble = 1 + Math.sin(i / 3) * 0.05;
    value = (value + monthly) * (1 + 0.008) * (drift / (1 + i * 0.011)) * wobble;
    const on = new Date(start);
    on.setUTCMonth(on.getUTCMonth() + i);
    points.push({
      on: on.toISOString().slice(0, 10),
      invested,
      value: Math.round(invested * (1 + 0.06 + i * 0.006) * wobble),
    });
  }
  return points;
}
