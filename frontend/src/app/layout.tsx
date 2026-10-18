import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/context/AuthContext";
import { Navbar } from "@/components/Navbar";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "AssessCraft AI — Agentic Academic Assessment Copilot",
  description: "Agentic Copilot for Academic Assessment Work powered by Gemini 3.1 Flash Lite (via OpenRouter), Google ADK, Vertex AI Search, and OR-Tools CP-SAT on Google Cloud.",
};

import React, { Suspense } from "react";

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-slate-50 text-slate-900 selection:bg-emerald-100 selection:text-emerald-900">
        <Suspense fallback={<div className="min-h-[60vh]" />}>
          <a
            href="#main"
            className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-[60] focus:px-3 focus:py-2 focus:rounded-lg focus:bg-white focus:text-slate-900 focus:shadow"
          >
            Skip to content
          </a>
          <AuthProvider>
            <Navbar />
            <main id="main" className="flex-1">{children}</main>
          </AuthProvider>
        </Suspense>
      </body>
    </html>
  );
}
