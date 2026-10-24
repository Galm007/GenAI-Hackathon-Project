import type { Metadata } from "next";
import { Inter, JetBrains_Mono, Fraunces, Caveat } from "next/font/google";
import { Toaster } from "@/components/ui/sonner";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains",
  display: "swap",
});

const fraunces = Fraunces({
  subsets: ["latin"],
  variable: "--font-fraunces",
  display: "swap",
});

const caveat = Caveat({
  subsets: ["latin"],
  variable: "--font-caveat",
  display: "swap",
});

export const metadata: Metadata = {
  title: "AdCom — Autonomous Admissions Committee",
  description: "Autonomous multi-agent university admissions committee simulator",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${inter.variable} ${jetbrainsMono.variable} ${fraunces.variable} ${caveat.variable} font-sans antialiased min-h-screen bg-[var(--color-room)] text-[var(--color-ink)]`}
      >
        {children}
        <Toaster />
      </body>
    </html>
  );
}
