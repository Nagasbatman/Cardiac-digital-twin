"use client";

import React, { useState } from "react";
import {
  Search,
  User,
  Users,
  CheckCircle2,
  Calendar,
  Layers,
  FileText,
  AlertTriangle,
  ChevronRight,
  Shield,
  ArrowRight,
} from "lucide-react";
import { PatientSummary, SampleProfile } from "@/types/cardiovascular_twin";

interface PatientCohortSelectorProps {
  selectedId: number | null;
  summary: PatientSummary | null;
  patientIds: number[];
  sampleProfiles: SampleProfile[];
  totalPatients: number;
  onSelectPatient: (subjectId: number) => void;
  isLoading: boolean;
}

export const PatientCohortSelector: React.FC<PatientCohortSelectorProps> = ({
  selectedId,
  summary,
  patientIds,
  sampleProfiles,
  totalPatients,
  onSelectPatient,
  isLoading,
}) => {
  const [searchInput, setSearchInput] = useState("");
  const [customInput, setCustomInput] = useState("");

  const handleCustomSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const idNum = parseInt(customInput.trim(), 10);
    if (!isNaN(idNum) && idNum > 0) {
      onSelectPatient(idNum);
      setCustomInput("");
    }
  };

  const filteredPatientIds = patientIds.filter((id) =>
    searchInput ? String(id).includes(searchInput.trim()) : true
  );

  return (
    <div className="space-y-6">
      {/* Example Cohort Quick Selector */}
      <div className="rounded-2xl border border-slate-800 bg-[#0a1222]/90 p-5 sm:p-6 shadow-xl space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 className="text-base sm:text-lg font-bold text-white flex items-center gap-2">
              <Users className="w-4 h-4 text-teal-400" />
              Example Patient Cohort
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Select a verified profile from the 1,500-patient prototype dataset to inspect real longitudinal measurements.
            </p>
          </div>
          <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-slate-800 text-teal-300 border border-teal-500/20 w-fit">
            {totalPatients.toLocaleString()} Total Records
          </span>
        </div>

        {/* Curated Patient Profile Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {sampleProfiles.map((p, index) => {
            const isSelected = selectedId === p.subject_id;
            return (
              <button
                key={p.subject_id ?? `sample-profile-${index}`}
                type="button"
                onClick={() => onSelectPatient(p.subject_id)}
                disabled={isLoading}
                className={`text-left p-3.5 rounded-xl border transition-all cursor-pointer ${
                  isSelected
                    ? "bg-teal-500/15 border-teal-400/60 shadow-lg shadow-teal-500/10 ring-1 ring-teal-400/40"
                    : "bg-slate-900/70 border-slate-800 hover:border-slate-700 hover:bg-slate-800/60"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-bold text-white">#{p.subject_id}</span>
                  {isSelected && <CheckCircle2 className="w-3.5 h-3.5 text-teal-400" />}
                </div>
                <div className="mt-2 text-[11px] text-slate-300">
                  {p.gender === "F" ? "Female" : "Male"}, {p.anchor_age} yrs
                </div>
                <div className="mt-1 flex items-center justify-between text-[10px] text-slate-400">
                  <span>{p.observation_count} obs</span>
                  <span>{p.distinct_dates} dates</span>
                </div>
              </button>
            );
          })}
        </div>

        {/* Search & Custom ID Input Bar */}
        <div className="pt-2 flex flex-col md:flex-row items-center gap-3">
          {/* Quick Filter dropdown */}
          <div className="relative flex-1 w-full">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Filter patient ID list (e.g. 1002)..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className="w-full pl-9 pr-3 py-2 rounded-xl bg-slate-900 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-teal-500/60"
            />
          </div>

          <div className="flex items-center gap-2 w-full md:w-auto">
            <select
              aria-label="Select from filtered patient IDs"
              value={selectedId || ""}
              onChange={(e) => {
                const val = parseInt(e.target.value, 10);
                if (!isNaN(val)) onSelectPatient(val);
              }}
              className="px-3 py-2 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-200 focus:outline-none focus:border-teal-500/60 w-full md:w-48 cursor-pointer"
            >
              <option value="">Choose Patient ID ({filteredPatientIds.length})</option>
              {filteredPatientIds.slice(0, 100).map((id) => (
                <option key={id} value={id}>
                  Patient #{id}
                </option>
              ))}
            </select>

            <form onSubmit={handleCustomSubmit} className="flex items-center gap-1.5 shrink-0">
              <input
                type="number"
                placeholder="Direct ID..."
                value={customInput}
                onChange={(e) => setCustomInput(e.target.value)}
                className="w-24 px-2.5 py-2 rounded-xl bg-slate-900 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-teal-500/60"
              />
              <button
                type="submit"
                className="px-3 py-2 rounded-xl bg-teal-600/30 hover:bg-teal-600/50 text-teal-300 border border-teal-500/40 text-xs font-semibold cursor-pointer"
              >
                Go
              </button>
            </form>
          </div>
        </div>
      </div>

      {/* Patient Profile Detailed Summary */}
      {summary && (
        <div className="rounded-2xl border border-slate-800 bg-[#0a1222]/90 p-5 sm:p-6 shadow-xl space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <User className="w-4 h-4 text-cyan-400" />
              Patient Profile &amp; Clinical Coverage Summary
            </h3>
            <span className="text-[11px] font-mono text-teal-400">ID: {summary.subject_id}</span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
            <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-3">
              <div className="text-slate-400 font-medium">Demographics</div>
              <div className="text-white font-bold text-sm mt-1">
                {summary.demographics.gender === "F" ? "Female" : "Male"}, {summary.demographics.anchor_age} years
              </div>
              <div className="text-slate-500 text-[10px] mt-0.5">Anchor group: {summary.demographics.anchor_year_group}</div>
            </div>

            <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-3">
              <div className="text-slate-400 font-medium">Observations &amp; Dates</div>
              <div className="text-white font-bold text-sm mt-1">
                {summary.total_observations} records across {summary.distinct_dates_count} dates
              </div>
              <div className="text-slate-500 text-[10px] mt-0.5">Admissions represented: {summary.admissions_represented_count}</div>
            </div>

            <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-3">
              <div className="text-slate-400 font-medium">Data Integrity Flags</div>
              <div className="text-amber-300 font-bold text-sm mt-1">
                {summary.unrecorded_units_count} unrecorded units
              </div>
              <div className="text-slate-500 text-[10px] mt-0.5">
                {summary.missing_values_count} missing values | {summary.requires_review_count} review flags
              </div>
            </div>

            <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-3">
              <div className="text-slate-400 font-medium">Simulation Eligibility</div>
              <div className="text-rose-400 font-bold text-sm mt-1 flex items-center gap-1.5">
                <AlertTriangle className="w-3.5 h-3.5 text-rose-400 shrink-0" />
                Generic Scenarios Only
              </div>
              <div className="text-slate-500 text-[10px] mt-0.5">Lacks empirical ODE state inputs</div>
            </div>
          </div>

          {/* Clinical Domains Coverage Badges */}
          <div className="pt-2 flex flex-wrap items-center gap-2">
            <span className="text-xs text-slate-400 font-medium mr-1">Covered Domains:</span>
            {summary.categories_present.map((cat, index) => (
              <span
                key={`${cat ?? "unknown-present"}-${index}`}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium bg-emerald-500/10 text-emerald-300 border border-emerald-500/30"
              >
                <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                {cat ?? "Unknown category"}
              </span>
            ))}
            {summary.categories_absent.map((cat, index) => (
              <span
                key={`${cat ?? "unknown-absent"}-${index}`}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium bg-slate-800/60 text-slate-400 border border-slate-700/60"
              >
                &bull; {cat ?? "Unknown category"} (Unrecorded)
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

