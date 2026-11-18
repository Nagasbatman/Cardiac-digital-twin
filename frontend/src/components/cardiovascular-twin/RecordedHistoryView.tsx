"use client";

import React, { useState } from "react";
import {
  TrendingUp,
  Table as TableIcon,
  Filter,
  Calendar,
  Layers,
  FileSpreadsheet,
  ChevronLeft,
  ChevronRight,
  Info,
  CheckCircle2,
  AlertTriangle,
} from "lucide-react";
import {
  ClinicalObservation,
  TrendCategory,
} from "@/types/cardiovascular_twin";

interface RecordedHistoryViewProps {
  trends: TrendCategory[];
  observations: ClinicalObservation[];
  totalObservations: number;
  isLoading: boolean;
  currentPage: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  selectedFilter: string;
  onFilterChange: (filter: string) => void;
}

export const RecordedHistoryView: React.FC<RecordedHistoryViewProps> = ({
  trends,
  observations,
  totalObservations,
  isLoading,
  currentPage,
  pageSize,
  onPageChange,
  selectedFilter,
  onFilterChange,
}) => {
  const [viewTab, setViewTab] = useState<"charts" | "table">("charts");

  const totalPages = Math.max(1, Math.ceil(totalObservations / pageSize));

  // Extract unique measurement names from observations
  const measurementOptions = [
    "All",
    "systolic_blood_pressure",
    "diastolic_blood_pressure",
    "troponin_t",
    "troponin_i",
    "total_cholesterol",
    "hdl_cholesterol",
    "ldl_cholesterol_calculated",
    "triglycerides",
    "hba1c",
    "creatinine",
  ];

  return (
    <section className="space-y-5">
      {/* Section Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-teal-400 tracking-wider uppercase">Section 02</span>
            <span className="text-slate-600">&bull;</span>
            <h2 className="text-lg sm:text-xl font-bold text-white tracking-tight">
              Recorded Cardiovascular History
            </h2>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Empirical historical measurements recorded in clinical encounters. Values are plotted without interpolation.
          </p>
        </div>

        {/* View Toggle */}
        <div className="flex items-center gap-1.5 p-1 rounded-xl bg-slate-900 border border-slate-800">
          <button
            type="button"
            onClick={() => setViewTab("charts")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
              viewTab === "charts"
                ? "bg-teal-500/20 text-teal-300 border border-teal-500/30 shadow-sm"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <TrendingUp className="w-3.5 h-3.5" />
            <span>Trend Charts</span>
          </button>
          <button
            type="button"
            onClick={() => setViewTab("table")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
              viewTab === "table"
                ? "bg-teal-500/20 text-teal-300 border border-teal-500/30 shadow-sm"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <TableIcon className="w-3.5 h-3.5" />
            <span>Observation Log ({totalObservations})</span>
          </button>
        </div>
      </div>

      {/* Measurement Filter Strip */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-thin">
        <Filter className="w-3.5 h-3.5 text-slate-500 shrink-0" />
        <span className="text-xs text-slate-400 font-medium shrink-0">Filter:</span>
        {measurementOptions.map((opt) => {
          const isSelected = selectedFilter === opt;
          return (
            <button
              key={opt}
              type="button"
              onClick={() => onFilterChange(opt)}
              className={`px-3 py-1 rounded-lg text-xs font-medium whitespace-nowrap transition-all cursor-pointer ${
                isSelected
                  ? "bg-teal-600 text-white font-semibold shadow-md shadow-teal-600/20"
                  : "bg-slate-900 text-slate-400 hover:bg-slate-800 hover:text-slate-200 border border-slate-800"
              }`}
            >
              {opt === "All"
                ? "All Measurements"
                : opt.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
            </button>
          );
        })}
      </div>

      {/* Main Content Area */}
      {viewTab === "charts" ? (
        <div className="space-y-6">
          {trends.length === 0 ? (
            <div className="rounded-2xl border border-slate-800 bg-[#0a1222]/80 p-8 text-center text-sm text-slate-400">
              No longitudinal trend series available for this patient selection.
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
              {trends.map((t, index) => (
                <div
                  key={`${t.category ?? "unknown-trend"}-${index}`}
                  className="rounded-2xl border border-slate-800 bg-[#0a1222]/90 p-5 shadow-xl space-y-4"
                >
                  <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
                    <div className="flex items-center gap-2">
                      <h3 className="text-sm font-bold text-white">{t.category}</h3>
                      <span className="text-xs text-slate-400">({t.unit})</span>
                    </div>
                    <span className="text-[11px] font-mono text-teal-400 bg-teal-500/10 px-2 py-0.5 rounded border border-teal-500/20">
                      {t.data_table.length} data points
                    </span>
                  </div>

                  {/* SVG Chart Container */}
                  <div
                    className="w-full overflow-x-auto rounded-xl bg-slate-950/80 p-3 border border-slate-850 flex justify-center"
                    dangerouslySetInnerHTML={{ __html: t.svg_chart }}
                  />

                  {/* Accessible Mini Table */}
                  <div className="overflow-x-auto max-h-40 overflow-y-auto scrollbar-thin">
                    <table className="w-full text-left text-[11px]">
                      <thead className="bg-slate-900/80 text-slate-400 sticky top-0">
                        <tr>
                          <th className="py-1 px-2 font-medium">Date</th>
                          <th className="py-1 px-2 font-medium">Parameter</th>
                          <th className="py-1 px-2 font-medium">Value</th>
                          <th className="py-1 px-2 font-medium">Source</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-850 text-slate-300">
                        {t.data_table.slice(0, 15).map((row, rIdx) => (
                          <tr key={rIdx} className="hover:bg-slate-800/40">
                            <td className="py-1 px-2 font-mono text-slate-400">{row.date}</td>
                            <td className="py-1 px-2 font-medium text-white">{row.display_name}</td>
                            <td className="py-1 px-2 font-mono font-bold text-teal-300">
                              {row.value_str} {row.unit}
                            </td>
                            <td className="py-1 px-2 text-slate-400">{row.source_label || "MIMIC-IV"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : (
        /* Tabular Observation Log View */
        <div className="rounded-2xl border border-slate-800 bg-[#0a1222]/90 p-5 shadow-xl space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-300">
              Showing page {currentPage} of {totalPages} ({totalObservations} observations)
            </span>

            {/* Pagination Controls */}
            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={() => onPageChange(currentPage - 1)}
                disabled={currentPage <= 1 || isLoading}
                className="p-1.5 rounded-lg border border-slate-800 bg-slate-900 text-slate-300 hover:bg-slate-800 disabled:opacity-40 cursor-pointer"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="text-xs font-mono text-slate-400 px-2">
                {currentPage} / {totalPages}
              </span>
              <button
                type="button"
                onClick={() => onPageChange(currentPage + 1)}
                disabled={currentPage >= totalPages || isLoading}
                className="p-1.5 rounded-lg border border-slate-800 bg-slate-900 text-slate-300 hover:bg-slate-800 disabled:opacity-40 cursor-pointer"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>

          <div className="overflow-x-auto rounded-xl border border-slate-800/80">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900 text-slate-400 uppercase text-[10px] tracking-wider font-semibold">
                <tr>
                  <th className="py-2.5 px-3">Event Date</th>
                  <th className="py-2.5 px-3">Measurement</th>
                  <th className="py-2.5 px-3">Value</th>
                  <th className="py-2.5 px-3">Unit</th>
                  <th className="py-2.5 px-3">Source</th>
                  <th className="py-2.5 px-3">Admission ID</th>
                  <th className="py-2.5 px-3">Review Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80 text-slate-300">
                {observations.map((obs, idx) => (
                  <tr key={idx} className="hover:bg-slate-800/30">
                    <td className="py-2 px-3 font-mono text-slate-400">{obs.event_date || "—"}</td>
                    <td className="py-2 px-3 font-medium text-white">{obs.display_name}</td>
                    <td className="py-2 px-3 font-mono font-bold text-teal-300">
                      {obs.value_numeric !== null ? obs.value_numeric : "None"}
                    </td>
                    <td className="py-2 px-3 text-slate-400">{obs.measurement_unit || "—"}</td>
                    <td className="py-2 px-3 text-slate-400">{obs.source}</td>
                    <td className="py-2 px-3 font-mono text-slate-400">
                      {obs.hadm_id ? `#${obs.hadm_id}` : "Outpatient"}
                    </td>
                    <td className="py-2 px-3">
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium ${
                          obs.value_review_status === "No issue identified"
                            ? "bg-emerald-500/10 text-emerald-300 border border-emerald-500/20"
                            : "bg-amber-500/10 text-amber-300 border border-amber-500/20"
                        }`}
                      >
                        {obs.value_review_status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  );
};

