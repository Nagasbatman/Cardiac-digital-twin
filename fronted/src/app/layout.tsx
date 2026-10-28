import type { Metadata } from "next";
import React from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: "PulseTwin | Cardiac MRI Segmentation & Diagnosis",
  description:
    "Unified Cardiac Digital Twin delivering 4-fold ensemble segmentation (RV, Myocardium, LV), 23 clinical biomarkers, and 5-class ACDC cardiomyopathy classification.",
  keywords: [
    "Cardiac MRI",
    "Digital Twin",
    "Deep Learning",
    "DINOv2",
    "Segmentation",
    "Cardiomyopathy",
    "Biomarkers",
    "ACDC",
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
      </head>
      <body className="min-h-screen bg-[#070b14] text-slate-100 antialiased selection:bg-cyan-500/30 selection:text-cyan-200">
        {children}
      </body>
    </html>
  );
}
