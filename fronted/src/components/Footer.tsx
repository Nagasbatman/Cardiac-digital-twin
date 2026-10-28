"use client";

import React from "react";
import { Heart, BookOpen, ExternalLink, ShieldAlert, Cpu } from "lucide-react";

export const Footer: React.FC = () => {
  return (
    <footer className="w-full border-t border-slate-800/80 bg-[#070b14] py-8 text-xs text-slate-500">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-6">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-slate-300 font-semibold">
              <Heart className="w-4 h-4 text-cyan-400" />
              <span>PULSE Cardiac Digital Twin Platform</span>
            </div>
            <p className="text-slate-500 max-w-xl text-[11px]">
              DINOv2 ViT-B/14 foundation model with Dense Prediction Transformer (DPT) decoder,
              4-fold stratified ensemble (folds 0–3), and biomarker-driven 5-class ACDC diagnosis.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-4 text-[11px]">
            <a
              href="https://ieeexplore.ieee.org/document/11660344"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-slate-400 hover:text-cyan-400 transition"
            >
              <BookOpen className="w-3.5 h-3.5" />
              <span>IEEE JBHI 2026 Paper</span>
              <ExternalLink className="w-3 h-3" />
            </a>
            <a
              href="https://huggingface.co/hg-0403/PULSE"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-slate-400 hover:text-cyan-400 transition"
            >
              <span>Hugging Face Weights</span>
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        </div>

        <div className="pt-4 border-t border-slate-800/60 flex flex-col sm:flex-row items-center justify-between gap-3 text-[11px]">
          <div className="flex items-center gap-1.5 text-amber-500/80">
            <ShieldAlert className="w-3.5 h-3.5 flex-shrink-0" />
            <span>
              For medical research and educational use only; not a certified diagnostic device.
            </span>
          </div>
          <div className="text-slate-500 font-mono">
            Dual Interface: Next.js Port 3000 • Gradio Port 7860
          </div>
        </div>
      </div>
    </footer>
  );
};
