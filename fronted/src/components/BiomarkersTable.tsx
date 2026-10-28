"use client";

import React, { useState } from "react";
import {
  FileText,
  Search,
  Activity,
  Heart,
  TrendingUp,
  Layers,
  Sparkles,
  Download,
  Filter
} from "lucide-react";
import { Biomarker } from "@/types/cardiac";

interface BiomarkersTableProps {
  biomarkers: Biomarker[];
}

export const BiomarkersTable: React.FC<BiomarkersTableProps> = ({
  biomarkers,
}) => {
  const [activeCategory, setActiveCategory] = useState<string>("All");
  const [searchQuery, setSearchQuery] = useState<string>("");

  const categories = [
    "All",
    "LV Function",
    "RV Function",
    "Myocardium",
    "BSA-Indexed",
    "Geometry & Ratios",
    "Wall Thickness",
  ];

  // Quick lookup helper for top KPI cards
  const getVal = (key: string) => {
    const item = biomarkers.find((b) => b.key === key);
    return item ? item.value : null;
  };

  const lvef = getVal("LV_EF");
  const lvedv = getVal("LV_EDV");
  const rvef = getVal("RV_EF");
  const lvmi = getVal("LVMi");

  const filteredBiomarkers = biomarkers.filter((b) => {
    const matchesCat =
      activeCategory === "All" || b.category === activeCategory;
    const matchesQuery =
      searchQuery.trim() === "" ||
      b.key.toLowerCase().includes(searchQuery.toLowerCase()) ||
      b.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      b.unit.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCat && matchesQuery;
  });

  const exportCSV = () => {
    const headers = ["Biomarker", "Description", "Value", "Unit", "Category", "Normal Range"];
    const rows = biomarkers.map((b) => [
      b.key,
      `"${b.description}"`,
      b.value,
      `"${b.unit}"`,
      `"${b.category}"`,
      `"${b.normal_range || ""}"`,
    ]);
    const csvContent =
      "data:text/csv;charset=utf-8," +
      [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "pulse_23_cardiac_biomarkers.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="glass-panel p-5 sm:p-6 space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-3 border-b border-slate-800">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-emerald-950/60 border border-emerald-800/40 text-emerald-400">
            <Activity className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              Extracted Clinical Cardiac Biomarkers
              <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">
                23 Indices
              </span>
            </h3>
            <p className="text-xs text-slate-400">
              Ventricle volumetrics, ejection fractions, indexed wall dimensions & geometry
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={exportCSV}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs font-medium text-slate-300 hover:text-white hover:border-slate-700 transition"
        >
          <Download className="w-3.5 h-3.5 text-cyan-400" />
          <span>Export CSV</span>
        </button>
      </div>

      {/* Top 4 Essential Clinical Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        {/* LVEF */}
        <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800/90 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>LV Ejection Fraction</span>
            <span className="w-2 h-2 rounded-full bg-cyan-400" />
          </div>
          <div className="my-1.5 flex items-baseline gap-1">
            <span className="text-2xl font-bold font-mono text-white">
              {lvef !== null ? lvef : "—"}
            </span>
            <span className="text-xs text-cyan-400">%</span>
          </div>
          <span className="text-[10px] text-slate-500">
            Normal: 55 - 75 %
          </span>
        </div>

        {/* LV EDV */}
        <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800/90 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>LV End-Diastolic Vol</span>
            <span className="w-2 h-2 rounded-full bg-blue-400" />
          </div>
          <div className="my-1.5 flex items-baseline gap-1">
            <span className="text-2xl font-bold font-mono text-white">
              {lvedv !== null ? lvedv : "—"}
            </span>
            <span className="text-xs text-blue-400">mL</span>
          </div>
          <span className="text-[10px] text-slate-500">
            Normal: 100 - 180 mL
          </span>
        </div>

        {/* RVEF */}
        <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800/90 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>RV Ejection Fraction</span>
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
          </div>
          <div className="my-1.5 flex items-baseline gap-1">
            <span className="text-2xl font-bold font-mono text-white">
              {rvef !== null ? rvef : "—"}
            </span>
            <span className="text-xs text-emerald-400">%</span>
          </div>
          <span className="text-[10px] text-slate-500">
            Normal: 45 - 65 %
          </span>
        </div>

        {/* LVMi */}
        <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800/90 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>LV Mass Indexed (LVMi)</span>
            <span className="w-2 h-2 rounded-full bg-purple-400" />
          </div>
          <div className="my-1.5 flex items-baseline gap-1">
            <span className="text-2xl font-bold font-mono text-white">
              {lvmi !== null ? lvmi : "—"}
            </span>
            <span className="text-xs text-purple-400">g/m²</span>
          </div>
          <span className="text-[10px] text-slate-500">
            Normal: 50 - 90 g/m²
          </span>
        </div>
      </div>

      {/* Filter Tabs & Search Controls */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 pt-1">
        {/* Category Pills */}
        <div className="flex items-center gap-1 overflow-x-auto pb-1 sm:pb-0 text-xs scrollbar-none">
          {categories.map((cat) => (
            <button
              key={cat}
              type="button"
              onClick={() => setActiveCategory(cat)}
              className={`px-3 py-1.5 rounded-lg whitespace-nowrap font-medium transition ${
                activeCategory === cat
                  ? "bg-slate-800 text-cyan-400 border border-cyan-500/30"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        {/* Search Input */}
        <div className="relative min-w-[220px]">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            placeholder="Search 23 biomarkers..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 rounded-lg bg-slate-950/80 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
          />
        </div>
      </div>

      {/* Biomarkers Table */}
      <div className="overflow-x-auto rounded-xl border border-slate-800/80">
        <table className="w-full text-left text-xs text-slate-300">
          <thead className="bg-slate-900/90 text-[11px] text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
            <tr>
              <th className="py-3 px-4">Biomarker</th>
              <th className="py-3 px-4">Description</th>
              <th className="py-3 px-4">Category</th>
              <th className="py-3 px-4 text-right">Measured Value</th>
              <th className="py-3 px-4">Unit</th>
              <th className="py-3 px-4">Reference Normal</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 bg-slate-950/40">
            {filteredBiomarkers.length > 0 ? (
              filteredBiomarkers.map((b) => (
                <tr
                  key={b.key}
                  className="hover:bg-slate-900/50 transition-colors"
                >
                  <td className="py-2.5 px-4 font-mono font-bold text-cyan-400 whitespace-nowrap">
                    {b.key}
                  </td>
                  <td className="py-2.5 px-4 font-medium text-slate-200">
                    {b.description}
                  </td>
                  <td className="py-2.5 px-4">
                    <span className="px-2 py-0.5 rounded-md text-[10px] bg-slate-900 border border-slate-800 text-slate-400">
                      {b.category}
                    </span>
                  </td>
                  <td className="py-2.5 px-4 text-right font-mono font-semibold text-white">
                    {b.value.toFixed(2)}
                  </td>
                  <td className="py-2.5 px-4 font-mono text-slate-400">
                    {b.unit}
                  </td>
                  <td className="py-2.5 px-4 text-slate-400 font-mono text-[11px]">
                    {b.normal_range || "—"}
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td
                  colSpan={6}
                  className="py-8 text-center text-slate-500 text-xs"
                >
                  No biomarkers match &ldquo;{searchQuery}&rdquo; in {activeCategory}.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
