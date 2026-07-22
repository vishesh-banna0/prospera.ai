import type { Metadata } from "next";
import { Archivo, IBM_Plex_Sans, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";
import { AuthProvider } from "@/features/auth/AuthProvider";
import { AuthBoundary } from "@/features/auth/AuthBoundary";

// Three roles — see DESIGN.md §2. Archivo is a sturdy grotesque used only for
// display, set in tracked uppercase for the engraved-panel-label feel.
const display = Archivo({
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
});
const sans = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-sans",
  display: "swap",
});
const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Prospera — instrument",
  description: "The console of a machine that watches markets and forms opinions, in rupees.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${display.variable} ${sans.variable} ${mono.variable}`}>
      <body>
        <Providers>
          <AuthProvider>
            <AuthBoundary>{children}</AuthBoundary>
          </AuthProvider>
        </Providers>
      </body>
    </html>
  );
}
