import Link from "next/link";

/**
 * Temporary landing while product screens are built out (frontend prompt §6).
 * Portfolio is live; the rest land in order.
 */
export default function HomePage() {
  return (
    <div className="mx-auto max-w-2xl px-6 py-16">
      <p className="eyebrow">System</p>
      <h1 className="mt-2 font-display text-xl font-bold text-fg">Prospera console</h1>
      <p className="mt-3 max-w-prose text-sm text-fg-dim">
        Virtual cash, real prices, machine opinions — in rupees. The Portfolio
        Center is live; Markets and Intelligence follow.
      </p>
      <div className="mt-6 flex flex-wrap gap-2">
        <Link
          href="/portfolio"
          className="inline-flex items-center rounded border border-fg bg-fg px-3 py-2 text-xs font-medium text-ink hover:bg-fg/90"
        >
          Open Portfolio Center →
        </Link>
        <Link
          href="/styleguide"
          className="inline-flex items-center rounded border border-line-2 bg-panel-2 px-3 py-2 text-xs font-medium text-fg hover:border-fg-mute"
        >
          View styleguide
        </Link>
      </div>
    </div>
  );
}
