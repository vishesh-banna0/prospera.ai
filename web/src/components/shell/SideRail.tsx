"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV } from "./nav";
import { cn } from "@/lib/cn";

/**
 * Dense, engraved-label navigation. The active item is marked by a fill plus a
 * hard left marker bar — not a colored glow (chrome carries no data color).
 */
export function SideRail() {
  const pathname = usePathname();

  return (
    <nav
      aria-label="Primary"
      className="hidden w-rail shrink-0 flex-col gap-5 overflow-y-auto border-r border-line bg-panel px-2 py-4 sm:flex"
    >
      {NAV.map((section) => (
        <div key={section.title}>
          <div className="eyebrow px-2 pb-1.5">{section.title}</div>
          <ul className="flex flex-col gap-0.5">
            {section.items.map((item) => {
              const active = pathname === item.href || pathname.startsWith(item.href + "/");
              if (!item.ready) {
                return (
                  <li key={item.href}>
                    <span
                      aria-disabled
                      className="flex cursor-default items-center justify-between rounded px-2 py-1.5 text-xs text-fg-mute"
                    >
                      {item.label}
                      <span className="font-mono text-[0.625rem] uppercase tracking-wider text-fg-mute/70">
                        soon
                      </span>
                    </span>
                  </li>
                );
              }
              return (
                <li key={item.href} className="relative">
                  {active && (
                    <span
                      className="absolute left-0 top-1/2 h-4 w-0.5 -translate-y-1/2 bg-fg"
                      aria-hidden
                    />
                  )}
                  <Link
                    href={item.href}
                    aria-current={active ? "page" : undefined}
                    className={cn(
                      "flex items-center rounded px-2 py-1.5 text-xs transition-colors",
                      active
                        ? "bg-panel-2 font-medium text-fg"
                        : "text-fg-dim hover:bg-panel-2 hover:text-fg",
                    )}
                  >
                    {item.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      ))}

      <p className="mt-auto px-2 font-mono text-[0.625rem] leading-relaxed text-fg-mute">
        Single local user. No account — auth arrives later.
      </p>
    </nav>
  );
}
