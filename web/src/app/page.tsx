import Link from "next/link";

/**
 * Temporary landing until the Portfolio screen is built (frontend prompt §6).
 * It opens on data everywhere else — this is only a signpost during the build.
 */
export default function HomePage() {
  return (
    <div className="mx-auto max-w-2xl px-6 py-16">
      <p className="eyebrow">System</p>
      <h1 className="mt-2 font-display text-xl font-bold text-fg">Instrument is being wired.</h1>
      <p className="mt-3 max-w-prose text-sm text-fg-dim">
        The frame, tokens, and core readouts are in place. Product screens land in
        order — Portfolio first. The design direction lives in the styleguide.
      </p>
      <Link
        href="/styleguide"
        className="mt-6 inline-flex items-center rounded border border-line-2 bg-panel-2 px-3 py-2 text-xs font-medium text-fg hover:border-fg-mute"
      >
        Open the styleguide →
      </Link>
    </div>
  );
}
