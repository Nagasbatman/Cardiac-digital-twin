"use client";

import React from "react";
import {
  ShieldAlert,
  RefreshCw,
  Database,
  Calendar,
  Layers,
  User,
  Info,
  Clock,
  Activity,
  Heart,
} from "lucide-react";
import { PatientSummary } from "@/types/cardiovascular_twin";

interface HeaderStatusAreaProps {
  summary: PatientSummary | null;
  selectedId: number | null;
  isLoading: boolean;
  onRefresh: () => void;
}

export const HeaderStatusArea: React.FC<HeaderStatusAreaProps> = ({
  summary,
  selectedId,
  isLoading,
  onRefresh,
}) => {
  return (
    <div className="space-y-4">
      {/* Dark Teal / Blue Hero Banner */}
      <div className="relative overflow-hidden rounded-2xl border border-teal-500/30 bg-gradient-to-br from-[#06202a] via-[#091b29] to-[#070e1b] p-6 sm:p-8 shadow-2xl shadow-teal-950/40">
        {/* Glow ambient background elements */}
        <div className="absolute -top-24 -right-24 w-96 h-96 rounded-full bg-teal-500/10 blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -left-24 w-96 h-96 rounded-full bg-cyan-500/10 blur-3xl pointer-events-none" />

        <div className="relative z-10 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
          {/* Title & Scope */}
          <div className="space-y-2 max-w-3xl">
            <div className="flex flex-wrap items-center gap-2.5">
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-teal-500/20 text-teal-300 border border-teal-400/30 shadow-sm">
                <Database className="w-3.5 h-3.5 text-teal-400" />
                Module III · Research Data
              </span>
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-800/80 text-slate-300 border border-slate-700">
                MIMIC-IV Prototype (1,500 Patients)
              </span>
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-500/10 text-amber-300 border border-amber-500/30">
                <Clock className="w-3 h-3 text-amber-400" />
                De-identified Chronology
              </span>
            </div>

            <h1 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold text-white tracking-tight flex items-center gap-3">
              <span>Cardiovascular Digital Twin</span>
            </h1>

            <p className="text-sm sm:text-base text-slate-300 font-normal leading-relaxed">
              Longitudinal cardiovascular patient records and lumped-parameter scenario workspace. Inspects verified clinical observations and evaluates mathematical hemodynamics via the CardioSim ODE solver.
            </p>
          </div>

          {/* Action & Refresh */}
          <div className="flex flex-row lg:flex-col items-center lg:items-end justify-between gap-3">
            <button
              onClick={onRefresh}
              disabled={isLoading}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold text-teal-200 bg-teal-900/40 hover:bg-teal-800/60 border border-teal-500/40 transition-all hover:shadow-lg hover:shadow-teal-500/20 disabled:opacity-50 cursor-pointer"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin text-teal-400" : ""}`} />
              <span>{isLoading ? "Refreshing..." : "Refresh Data"}</span>
            </button>

            {summary && (
              <div className="text-right hidden sm:block">
                <div className="text-[11px] text-slate-400 font-mono">Cohort Base: MIMIC-IV</div>
                <div className="text-xs text-teal-400 font-medium">Record ID: {summary.subject_id}</div>
              </div>
            )}
          </div>
        </div>

        {/* Selected Patient Live Telemetry Bar */}
        {summary ? (
          <div className="mt-6 pt-5 border-t border-teal-900/40 grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
            <div className="bg-slate-900/60 border border-teal-900/30 rounded-xl p-3">
              <div className="text-[11px] font-semibold uppercase tracking-wider text-teal-400/80 flex items-center gap-1.5">
                <User className="w-3 h-3 text-teal-400" /> Active Patient
              </div>
              <div className="text-lg font-bold text-white mt-0.5">#{summary.subject_id}</div>
              <div className="text-[10px] text-slate-400">{summary.demographics.gender === "F" ? "Female" : "Male"}, {summary.demographics.anchor_age} yrs</div>
            </div>

            <div className="bg-slate-900/60 border border-teal-900/30 rounded-xl p-3">
              <div className="text-[11px] font-semibold uppercase tracking-wider text-teal-400/80 flex items-center gap-1.5">
                <Layers className="w-3 h-3 text-teal-400" /> Observations
              </div>
              <div className="text-lg font-bold text-teal-300 mt-0.5">{summary.total_observations}</div>
              <div className="text-[10px] text-slate-400">Total lab &amp; vital records</div>
            </div>

            <div className="bg-slate-900/60 border border-teal-900/30 rounded-xl p-3">
              <div className="text-[11px] font-semibold uppercase tracking-wider text-teal-400/80 flex items-center gap-1.5">
                <Calendar className="w-3 h-3 text-teal-400" /> Dates
              </div>
              <div className="text-lg font-bold text-white mt-0.5">{summary.distinct_dates_count}</div>
              <div className="text-[10px] text-slate-400">Distinct clinical dates</div>
            </div>

            <div className="bg-slate-900/60 border border-teal-900/30 rounded-xl p-3">
              <div className="text-[11px] font-semibold uppercase tracking-wider text-teal-400/80 flex items-center gap-1.5">
                <Activity className="w-3 h-3 text-teal-400" /> Domains
              </div>
              <div className="text-lg font-bold text-white mt-0.5">{summary.categories_present.length} / 5</div>
              <div className="text-[10px] text-slate-400">Covered clinical domains</div>
            </div>

            <div className="bg-slate-900/60 border border-teal-900/30 rounded-xl p-3">
              <div className="text-[11px] font-semibold uppercase tracking-wider text-amber-400/80 flex items-center gap-1.5">
                <Info className="w-3 h-3 text-amber-400" /> Data Flags
              </div>
              <div className="text-lg font-bold text-amber-300 mt-0.5">{summary.unrecorded_units_count}</div>
              <div className="text-[10px] text-slate-400">Unrecorded unit flags</div>
            </div>

            <div className="bg-slate-900/60 border border-teal-900/30 rounded-xl p-3">
              <div className="text-[11px] font-semibold uppercase tracking-wider text-cyan-400/80 flex items-center gap-1.5">
                <Clock className="w-3 h-3 text-cyan-400" /> Year Group
              </div>
              <div className="text-base font-bold text-cyan-300 mt-1 truncate">{summary.demographics.anchor_year_group}</div>
              <div className="text-[10px] text-slate-400">Anchor period</div>
            </div>
          </div>
        ) : (
          <div className="mt-4 p-3 rounded-xl bg-slate-900/40 border border-slate-800 text-xs text-slate-400">
            No patient selected. Choose an example patient or search by ID below to load clinical measurements.
          </div>
        )}
      </div>

      {/* De-identification & Research Data Notice Banner */}
      <div className="p-3.5 rounded-xl border border-amber-500/25 bg-amber-500/5 text-amber-200/90 text-xs flex items-start gap-2.5">
        <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
        <div className="space-y-0.5">
          <span className="font-semibold text-amber-300">Research Prototype Notice: </span>
          <span>
            Dates in this dataset are chronologically shifted and de-identified per HIPAA Safe Harbor provisions; they reflect longitudinal intervals rather than real-world calendar dates. Observations represent verified prototype records without interpolation.
          </span>
        </div>
      </div>
    </div>
  );
};

