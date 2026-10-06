import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";

import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Worship Mix",
  description: "Hear the room, trust the mix, serve the song.",
  applicationName: "Worship Mix",
  manifest: "/manifest.webmanifest",
  appleWebApp: { capable: true, title: "Worship Mix", statusBarStyle: "black-translucent" },
};

export const viewport: Viewport = {
  themeColor: "#09090c",
  colorScheme: "dark",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable}`}>{children}</body>
    </html>
  );
}
