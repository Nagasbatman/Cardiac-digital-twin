"use client";

import React from "react";
import {
  Activity,
  Heart,
  Droplet,
  Flame,
  Calendar,
  Layers,
  AlertCircle,
  CheckCircle2,
  HelpCircle,
  TrendingUp,
} from "lucide-react";
import { CategoryAnalysis } from "@/types/cardiovascular_twin";

interface CurrentCardiovascularStateProps {
  analysis: CategoryAnalysis[];
  isLoading: boolean;
}

const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  "Blood Pressure": <Activity className="w-4 h-4 text-rose-400" />,
  "Cardiac Troponin": <Heart className="w-4 h-4 text-red-400" />,
  "Lipid Profile": <Droplet className="w-4 h-4 text-amber-400" />,
  "Glycemic Context": <Flame className="w-4 h-4 text-orange-400" />,
  "Renal Context": <Layers className="w-4 h-4 text-cyan-400" />,
};

export const CurrentCardiovascularState: React.FC<CurrentCardiovascularStateProps> = ({
  analysis,
  isLoading,
}) => {
  return (
    <section className="space-y-4">
      {/* Section Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-teal-400 tracking-wider uppercase">Section 01</span>
            <span className="text-slate-600">&bull;</span>
            <h2 className="text-lg sm:text-xl font-bold text-white tracking-tight">
              Current Cardiovascular State
            </h2>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Categorized synthesis of available cardiovascular observations from clinical records.
          </p>
        </div>
        <span className="text-xs text-slate-400 font-mono">
          {analysis.length} Clinical Domains Synthesized
        </span>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5].map((idx) => (
            <div
              key={idx}
              className="h-44 rounded-2xl border border-slate-800 bg-[#0a1222]/60 animate-pulse p-5"
            />
          ))}
        </div>
      ) : analysis.length === 0 ? (
        <div className="rounded-2xl border border-slate-800 bg-[#0a1222]/80 p-8 text-center space-y-2">
          <HelpCircle className="w-8 h-8 text-slate-600 mx-auto" />
          <p className="text-sm text-slate-400">
            No cardiovascular domain observations recorded for this patient profile.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {analysis.map((cat, index) => {
            const hasData = cat.observation_count > 0;
            return (
              <div
                key={`${cat.category ?? "unknown-analysis"}-${index}`}
                className={`rounded-2xl border p-5 transition-all shadow-lg ${
                  hasData
                    ? "border-slate-800 bg-[#0a1222]/90 hover:border-slate-700"
                    : "border-slate-850 bg-[#080d1a]/50 opacity-60"
                }`}
              >
                {/* Category Header */}
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2.5">
                    <div className="p-2 rounded-xl bg-slate-900 border border-slate-800">
                      {CATEGORY_ICONS[cat.category] || <Activity className="w-4 h-4 text-teal-400" />}
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-white">{cat.category}</h3>
                      <div className="text-[11px] text-slate-400 truncate max-w-[200px]" title={cat.fields.join(", ")}>
                        {cat.fields.join(", ")}
                      </div>
                    </div>
                  </div>
                  <span
                    className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                      hasData
                        ? "bg-teal-500/10 text-teal-400 border border-teal-500/20"
                        : "bg-slate-800 text-slate-500"
                    }`}
                  >
                    {cat.observation_count} obs
                  </span>
                </div>

                {/* Values & Ranges */}
                <div className="mt-4 pt-3 border-t border-slate-800/80 space-y-2 text-xs">
                  <div className="flex items-baseline justify-between">
                    <span className="text-slate-400">Latest Reading:</span>
                    <span className="font-bold text-white font-mono text-sm">{cat.latest_reading}</span>
                  </div>

                  <div className="flex items-center justify-between text-[11px]">
                    <span className="text-slate-400 flex items-center gap-1">
                      <Calendar className="w-3 h-3 text-slate-500" /> Date:
                    </span>
                    <span className="text-slate-300 font-mono">{cat.latest_date}</span>
                  </div>

                  <div className="flex items-center justify-between text-[11px]">
                    <span className="text-slate-400">Recorded Range:</span>
                    <span className="text-teal-300 font-mono">{cat.range}</span>
                  </div>

                  {/* Audit flags strip */}
                  <div className="mt-3 pt-2.5 border-t border-slate-850 flex items-center justify-between text-[10px] text-slate-400">
                    <span className="flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                      {cat.valid_count} valid numeric
                    </span>
                    {cat.unrecorded_units_count > 0 && (
                      <span className="text-amber-400 font-medium">
                        {cat.unrecorded_units_count} unit flags
                      </span>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
};

