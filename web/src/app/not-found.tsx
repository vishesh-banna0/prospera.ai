import Link from "next/link";

export default function NotFound() {
  return (
    <div className="mx-auto flex max-w-lg flex-col items-start px-6 py-20">
      <p className="eyebrow">No signal</p>
      <h1 className="mt-2 font-mono text-2xl text-fg tnum">404</h1>
      <p className="mt-3 text-sm text-fg-dim">
        No readout on this channel. The screen may not be built yet, or the address
        is wrong.
      </p>
      <Link
        href="/"
        className="mt-6 inline-flex items-center rounded border border-line-2 bg-panel-2 px-3 py-2 text-xs font-medium text-fg hover:border-fg-mute"
      >
        ← Back to the console
      </Link>
    </div>
  );
}
