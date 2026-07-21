import type { ReactNode } from "react";
import { StatusStrip } from "./StatusStrip";
import { SideRail } from "./SideRail";

/** The fixed instrument frame. Content scrolls inside; the frame never does. */
export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-dvh flex-col overflow-hidden">
      <StatusStrip />
      <div className="flex min-h-0 flex-1">
        <SideRail />
        <main className="min-w-0 flex-1 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
}
