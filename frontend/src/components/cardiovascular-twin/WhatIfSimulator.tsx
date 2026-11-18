"use client";

import React, { useState } from "react";
import {
  Play,
  RotateCcw,
  Sliders,
  AlertTriangle,
  Info,
  CheckCircle2,
  TrendingUp,
  TrendingDown,
  ArrowRight,
  ShieldAlert,
  GitCompare,
  Trash2,
  Download,
} from "lucide-react";
import {
  PresetInfo,
  ProvenanceReport,
  ScenarioComparisonView,
  ScenarioSummary,
  SimulationResponse,
} from "@/types/cardiovascular_twin";

interface WhatIfSimulatorProps {
  provenance: ProvenanceReport | null;
  presets: Record<string, PresetInfo>;
  selectedPreset: string;
  onSelectPreset: (preset: string) => void;
  onRunPreset: (presetName: string, duration: number) => Promise<void>;
  onRunWhatIf: (params: {
    scenario_name: string;
    preset_name: string;
    hr: number;
    contract: number;
    resist: number;
    compl: number;
    duration: number;
  }) => Promise<void>;
  simulationResult: SimulationResponse | null;
  scenarioComparison: ScenarioComparisonView | null;
  sessionScenarios: ScenarioSummary[];
  onClearHistory: () => Promise<void>;
  isLoading: boolean;
  errorMessage: string | null;
}

export const WhatIfSimulator: React.FC<WhatIfSimulatorProps> = ({
  provenance,
  presets,
  selectedPreset,
  onSelectPreset,
  onRunPreset,
  onRunWhatIf,
  simulationResult,
  scenarioComparison,
  sessionScenarios,
  onClearHistory,
  isLoading,
  errorMessage,
}) => {
  const [activeTab, setActiveTab] = useState<"preset" | "whatif">("preset");

  // Form states for what-if custom sliders
  const currentPresetInfo = presets[selectedPreset] || {
    hr: 75,
    contract: 100,
    resist: 1.0,
    compl: 1.46,
  };

  const [scenarioName, setScenarioName] = useState("Custom Hemodynamic Scenario");
  const [hr, setHr] = useState<number>(currentPresetInfo.hr || 75);
  const [contract, setContract] = useState<number>(currentPresetInfo.contract || 100);
  const [resist, setResist] = useState<number>(currentPresetInfo.resist || 1.0);
  const [compl, setCompl] = useState<number>(currentPresetInfo.compl || 1.46);
  const [duration, setDuration] = useState<number>(6.0);

  // Sync sliders when base preset changes
  const handleBasePresetChange = (name: string) => {
    onSelectPreset(name);
    const p = presets[name];
    if (p) {
      setHr(p.hr);
      setContract(p.contract);
      setResist(p.resist);
      setCompl(p.compl);
    }
  };

  const handleRunPresetSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onRunPreset(selectedPreset, duration);
  };

  const handleRunWhatIfSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onRunWhatIf({
      scenario_name: scenarioName,
      preset_name: selectedPreset,
      hr: Number(hr),
      contract: Number(contract),
      resist: Number(resist),
      compl: Number(compl),
      duration: Number(duration),
    });
  };

  // Derive active simulation metrics
  const simMetrics =
    simulationResult?.metrics ||
    (scenarioComparison?.current_scenario?.metrics ?? null);

  return (
    <section className="space-y-6">
      {/* Section Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-teal-400 tracking-wider uppercase">Section 03</span>
            <span className="text-slate-600">&bull;</span>
            <h2 className="text-lg sm:text-xl font-bold text-white tracking-tight">
              What-if Scenario Simulator
            </h2>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Evaluate cardiovascular hemodynamics using the CardioSim lumped-parameter ODE engine.
          </p>
        </div>

        {/* Tab switch between Preset and Custom What-if */}
        <div className="flex items-center gap-1.5 p-1 rounded-xl bg-slate-900 border border-slate-800">
          <button
            type="button"
            onClick={() => setActiveTab("preset")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
              activeTab === "preset"
                ? "bg-teal-500/20 text-teal-300 border border-teal-500/30 shadow-sm"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Clinical Presets
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("whatif")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
              activeTab === "whatif"
                ? "bg-teal-500/20 text-teal-300 border border-teal-500/30 shadow-sm"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Custom What-If Engine
          </button>
        </div>
      </div>

      {/* SUBSECTION A: Simulation Readiness & Provenance Table */}
      {provenance && (
        <div className="rounded-2xl border border-slate-800 bg-[#0a1222]/90 p-5 shadow-xl space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-amber-400" />
              Parameter Provenance &amp; Simulation Readiness
            </h3>
            <span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-amber-500/10 text-amber-300 border border-amber-500/20">
              Generic Presets / Assumed Parameters Only
            </span>
          </div>

          <p className="text-xs text-slate-300 leading-relaxed">
            {provenance.readiness_summary}
          </p>

          <div className="overflow-x-auto rounded-xl border border-slate-800/80 mt-2">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900 text-slate-400 uppercase text-[10px] tracking-wider font-semibold">
                <tr>
                  <th className="py-2 px-3">Simulator Parameter</th>
                  <th className="py-2 px-3">State Key</th>
                  <th className="py-2 px-3">Status</th>
                  <th className="py-2 px-3">Evidence Source</th>
                  <th className="py-2 px-3">Scientific Boundary Note</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80 text-slate-300">
                {provenance.parameters.map((p, index) => (
                  <tr key={`${p.field_name ?? "unknown-parameter"}-${index}`} className="hover:bg-slate-800/30">
                    <td className="py-2 px-3 font-semibold text-white">{p.display_name}</td>
                    <td className="py-2 px-3 font-mono text-teal-400"><code>{p.field_name}</code></td>
                    <td className="py-2 px-3">
                      <span
                        className={`inline-flex px-2 py-0.5 rounded text-[10px] font-bold ${
                          p.status === "ASSUMED"
                            ? "bg-slate-800 text-slate-300 border border-slate-700"
                            : p.status === "UNAVAILABLE"
                            ? "bg-rose-950/60 text-rose-300 border border-rose-800/60"
                            : "bg-teal-950 text-teal-300"
                        }`}
                      >
                        {p.status}
                      </span>
                    </td>
                    <td className="py-2 px-3 text-slate-400">{p.source}</td>
                    <td className="py-2 px-3 text-slate-300 text-[11px]">{p.notes}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Error Alert */}
      {errorMessage && (
        <div className="p-3.5 rounded-xl border border-rose-500/40 bg-rose-500/10 text-rose-300 text-xs flex items-center gap-2.5">
          <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* SUBSECTION B: Simulation Form (Preset vs What-If) */}
      <div className="rounded-2xl border border-slate-800 bg-[#0a1222]/90 p-5 sm:p-6 shadow-xl space-y-5">
        {activeTab === "preset" ? (
          /* Preset Mode */
          <form onSubmit={handleRunPresetSubmit} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="space-y-1.5 md:col-span-2">
                <label className="text-xs font-semibold text-slate-300">
                  CardioSim Lumped-Parameter Preset:
                </label>
                <select
                  value={selectedPreset}
                  onChange={(e) => handleBasePresetChange(e.target.value)}
                  className="w-full px-3 py-2.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-white focus:outline-none focus:border-teal-500 cursor-pointer"
                >
                  {Object.entries(presets).map(([pName, pInfo]) => (
                    <option key={pName} value={pName}>
                      {pName} (HR: {Math.round(pInfo.hr)} bpm, Contractility: {Math.round(pInfo.contract)}%, {pInfo.category})
                    </option>
                  ))}
                </select>
                {presets[selectedPreset] && (
                  <p className="text-[11px] text-slate-400 italic mt-1">
                    {presets[selectedPreset].desc}
                  </p>
                )}
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300">
                  Simulation Duration (seconds):
                </label>
                <input
                  type="number"
                  min="2.0"
                  max="20.0"
                  step="0.5"
                  value={duration}
                  onChange={(e) => setDuration(parseFloat(e.target.value))}
                  className="w-full px-3 py-2.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-white focus:outline-none focus:border-teal-500"
                />
                <span className="text-[10px] text-slate-500">Allowed range: 2.0 – 20.0s</span>
              </div>
            </div>

            <div className="pt-2 flex items-center justify-end">
              <button
                type="submit"
                disabled={isLoading}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold text-slate-950 bg-teal-400 hover:bg-teal-300 transition-all shadow-lg shadow-teal-500/20 disabled:opacity-50 cursor-pointer"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>{isLoading ? "Running ODE Simulation..." : "Run Simulation"}</span>
              </button>
            </div>
          </form>
        ) : (
          /* Custom What-If Form with Verified Bounds */
          <form onSubmit={handleRunWhatIfSubmit} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="space-y-1.5 sm:col-span-2">
                <label className="text-xs font-semibold text-slate-300">Scenario Name:</label>
                <input
                  type="text"
                  value={scenarioName}
                  onChange={(e) => setScenarioName(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-800 text-xs text-white focus:outline-none focus:border-teal-500"
                  required
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300">Base Preset Reference:</label>
                <select
                  value={selectedPreset}
                  onChange={(e) => handleBasePresetChange(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-800 text-xs text-white focus:outline-none focus:border-teal-500 cursor-pointer"
                >
                  {Object.keys(presets).map((name) => (
                    <option key={name} value={name}>
                      {name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* 4 Interactive Param Sliders with CardioSim Bounds */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 pt-2">
              {/* HR */}
              <div className="p-3.5 rounded-xl bg-slate-900/90 border border-slate-800 space-y-2">
                <div className="flex justify-between text-xs">
                  <span className="font-semibold text-slate-300">Heart Rate (hr)</span>
                  <span className="font-mono font-bold text-teal-400">{hr} bpm</span>
                </div>
                <input
                  type="range"
                  min="30"
                  max="400"
                  step="1"
                  value={hr}
                  onChange={(e) => setHr(Number(e.target.value))}
                  className="w-full accent-teal-400 cursor-pointer"
                />
                <div className="flex justify-between text-[10px] text-slate-500 font-mono">
                  <span>30 bpm</span>
                  <span>400 bpm</span>
                </div>
              </div>

              {/* Contractility */}
              <div className="p-3.5 rounded-xl bg-slate-900/90 border border-slate-800 space-y-2">
                <div className="flex justify-between text-xs">
                  <span className="font-semibold text-slate-300">Contractility (contract)</span>
                  <span className="font-mono font-bold text-teal-400">{contract}%</span>
                </div>
                <input
                  type="range"
                  min="10"
                  max="160"
                  step="1"
                  value={contract}
                  onChange={(e) => setContract(Number(e.target.value))}
                  className="w-full accent-teal-400 cursor-pointer"
                />
                <div className="flex justify-between text-[10px] text-slate-500 font-mono">
                  <span>10%</span>
                  <span>160%</span>
                </div>
              </div>

              {/* Resistance */}
              <div className="p-3.5 rounded-xl bg-slate-900/90 border border-slate-800 space-y-2">
                <div className="flex justify-between text-xs">
                  <span className="font-semibold text-slate-300">Resistance (resist)</span>
                  <span className="font-mono font-bold text-teal-400">{Number(resist).toFixed(2)}</span>
                </div>
                <input
                  type="range"
                  min="0.4"
                  max="2.5"
                  step="0.05"
                  value={resist}
                  onChange={(e) => setResist(Number(e.target.value))}
                  className="w-full accent-teal-400 cursor-pointer"
                />
                <div className="flex justify-between text-[10px] text-slate-500 font-mono">
                  <span>0.4 mmHg·s/mL</span>
                  <span>2.5</span>
                </div>
              </div>

              {/* Compliance */}
              <div className="p-3.5 rounded-xl bg-slate-900/90 border border-slate-800 space-y-2">
                <div className="flex justify-between text-xs">
                  <span className="font-semibold text-slate-300">Compliance (compl)</span>
                  <span className="font-mono font-bold text-teal-400">{Number(compl).toFixed(2)}</span>
                </div>
                <input
                  type="range"
                  min="0.6"
                  max="2.2"
                  step="0.02"
                  value={compl}
                  onChange={(e) => setCompl(Number(e.target.value))}
                  className="w-full accent-teal-400 cursor-pointer"
                />
                <div className="flex justify-between text-[10px] text-slate-500 font-mono">
                  <span>0.6 mL/mmHg</span>
                  <span>2.2</span>
                </div>
              </div>
            </div>

            <div className="pt-2 flex items-center justify-between">
              <span className="text-[11px] text-slate-400">
                All changes evaluated as independent what-if hypotheses.
              </span>
              <button
                type="submit"
                disabled={isLoading}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold text-slate-950 bg-cyan-400 hover:bg-cyan-300 transition-all shadow-lg shadow-cyan-500/20 disabled:opacity-50 cursor-pointer"
              >
                <Sliders className="w-3.5 h-3.5" />
                <span>{isLoading ? "Simulating What-If..." : "Run Custom Scenario"}</span>
              </button>
            </div>
          </form>
        )}
      </div>

      {/* SUBSECTION D: Structured Simulation Results Panel */}
      {simMetrics && (
        <div className="rounded-2xl border border-teal-500/30 bg-[#07131e]/95 p-6 shadow-2xl space-y-6">
          {/* Header Strip */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-teal-900/40 pb-4">
            <div>
              <div className="text-[11px] font-bold uppercase tracking-wider text-teal-400">
                Simulation Output · Lumped-Parameter Solver
              </div>
              <h3 className="text-xl font-extrabold text-white mt-0.5">
                {simulationResult?.scenario_label || scenarioComparison?.current_scenario?.name || "Scenario Results"}
              </h3>
            </div>
            <div className="flex items-center gap-2">
              <span className="px-3 py-1 rounded-full text-xs font-semibold bg-teal-500/20 text-teal-300 border border-teal-500/40">
                ODE Converged
              </span>
            </div>
          </div>

          {/* 3 Top KPI Cards */}
          {(() => {
            const ef = simMetrics.ef;
            const co = simMetrics.co;
            const map = simMetrics.map_val;

            let efBand = "Normal EF";
            let efColor = "text-emerald-400";
            if (ef < 40) {
              efBand = "Reduced EF";
              efColor = "text-rose-400";
            } else if (ef < 55) {
              efBand = "Mildly Reduced EF";
              efColor = "text-amber-400";
            }

            let routingAction = "MAP within target perfusion range";
            let routingNote = `MAP ${Math.round(map)} mmHg indicates standard arterial perfusion pressure.`;
            if (map > 100) {
              routingAction = "Elevated MAP — Review resistance & afterload";
              routingNote = `MAP ${Math.round(map)} mmHg > 100 mmHg; resistance-dominant hemodynamic pattern.`;
            } else if (map < 70) {
              routingAction = "Low MAP — Review preload & compliance";
              routingNote = `MAP ${Math.round(map)} mmHg < 70 mmHg; consider arterial compliance & heart rate.`;
            }

            return (
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                {/* KPI 1: Cardiac Output */}
                <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-4 space-y-1">
                  <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                    Cardiac Output
                  </div>
                  <div className="text-3xl font-extrabold text-cyan-400 font-mono">
                    {co.toFixed(2)}{" "}
                    <span className="text-xs font-normal text-slate-400">L/min</span>
                  </div>
                  <div className="text-xs text-slate-400 pt-1">
                    {co < 4.0
                      ? "Low forward flow (< 4.0 L/min)"
                      : co > 8.0
                      ? "Hyperdynamic output (> 8.0 L/min)"
                      : "Within normal resting range (4.0–8.0 L/min)"}
                  </div>
                </div>

                {/* KPI 2: Ejection Fraction & Decision Band */}
                <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-4 space-y-1">
                  <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                    Ejection Fraction
                  </div>
                  <div className={`text-3xl font-extrabold font-mono ${efColor}`}>
                    {ef.toFixed(1)}%
                  </div>
                  <div className="text-xs font-semibold text-white pt-1">
                    {efBand}{" "}
                    <span className="text-slate-400 font-normal text-[11px]">(Normal ≥ 55%)</span>
                  </div>
                </div>

                {/* KPI 3: Clinical Routing */}
                <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-4 space-y-1">
                  <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                    Hemodynamic Routing
                  </div>
                  <div className="text-sm font-bold text-teal-300 leading-snug">
                    &rarr; {routingAction}
                  </div>
                  <div className="text-[11px] text-slate-400 pt-1">{routingNote}</div>
                </div>
              </div>
            );
          })()}

          {/* Ejection Fraction Continuum Progress Bar */}
          <div className="space-y-1.5 bg-slate-900/70 border border-slate-800/80 rounded-xl p-4">
            <div className="flex justify-between text-xs text-slate-400">
              <span className="font-semibold text-slate-300">Ejection-Fraction Continuum</span>
              <span>Normal Reference: &ge; 55%</span>
            </div>
            <div className="relative h-3 w-full rounded-full bg-gradient-to-r from-rose-500 via-amber-400 to-emerald-400 overflow-visible">
              <div
                className="absolute -top-1 w-2.5 h-5 bg-white border-2 border-slate-950 rounded shadow-md -translate-x-1/2"
                style={{
                  left: `${Math.min(100, Math.max(0, (simMetrics.ef / 80) * 100))}%`,
                }}
              />
            </div>
            <div className="flex justify-between text-[10px] text-slate-500 font-mono pt-0.5">
              <span>0% (Severe)</span>
              <span className="text-teal-300 font-bold">Simulated EF: {simMetrics.ef.toFixed(1)}%</span>
              <span>80%+ (Hyperdynamic)</span>
            </div>
          </div>

          {/* Action Recommended / Clinical Context Banner */}
          <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-xs space-y-1">
            <div className="text-[11px] font-bold text-amber-300 uppercase tracking-wider">
              Clinical Simulation Context
            </div>
            <p className="text-amber-100/90 leading-relaxed">
              Simulated Mean Arterial Pressure is {Math.round(simMetrics.map_val)} mmHg with a Heart Rate of {Math.round(simMetrics.hr)} bpm, Stroke Volume of {simMetrics.sv.toFixed(1)} mL, and Pulse Pressure of {Math.round(simMetrics.pp)} mmHg. These values represent mathematical ODE solutions for the configured scenario parameters, strictly independent of measured patient records.
            </p>
          </div>

          {/* Simulated Cardiovascular Metrics Table */}
          <div className="space-y-2">
            <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">
              Simulated Cardiovascular Metrics (CardioSim Outputs)
            </h4>
            <div className="overflow-x-auto rounded-xl border border-slate-800">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-900 text-slate-400 uppercase text-[10px] tracking-wider font-semibold">
                  <tr>
                    <th className="py-2.5 px-3">Metric Name</th>
                    <th className="py-2.5 px-3">State Key</th>
                    <th className="py-2.5 px-3">Simulated Value</th>
                    <th className="py-2.5 px-3">Reference Range</th>
                    <th className="py-2.5 px-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800 text-slate-300">
                  {[
                    { name: "Cardiac Output", key: "co", val: simMetrics.co.toFixed(2), unit: "L/min", ref: "4.0 – 8.0", ok: simMetrics.co >= 4 && simMetrics.co <= 8 },
                    { name: "Stroke Volume", key: "sv", val: simMetrics.sv.toFixed(1), unit: "mL", ref: "60 – 100", ok: simMetrics.sv >= 60 && simMetrics.sv <= 100 },
                    { name: "Systolic Pressure", key: "sys", val: Math.round(simMetrics.sys), unit: "mmHg", ref: "100 – 130", ok: simMetrics.sys >= 100 && simMetrics.sys <= 130 },
                    { name: "Diastolic Pressure", key: "dia", val: Math.round(simMetrics.dia), unit: "mmHg", ref: "60 – 80", ok: simMetrics.dia >= 60 && simMetrics.dia <= 80 },
                    { name: "Mean Arterial Pressure", key: "map_val", val: Math.round(simMetrics.map_val), unit: "mmHg", ref: "70 – 100", ok: simMetrics.map_val >= 70 && simMetrics.map_val <= 100 },
                    { name: "Pulse Pressure", key: "pp", val: Math.round(simMetrics.pp), unit: "mmHg", ref: "30 – 50", ok: simMetrics.pp >= 30 && simMetrics.pp <= 50 },
                    { name: "Ejection Fraction", key: "ef", val: simMetrics.ef.toFixed(1), unit: "%", ref: "≥ 55", ok: simMetrics.ef >= 55 },
                    { name: "Heart Rate", key: "hr", val: Math.round(simMetrics.hr), unit: "bpm", ref: "60 – 100", ok: simMetrics.hr >= 60 && simMetrics.hr <= 100 },
                  ].map((row) => (
                    <tr key={row.key} className="hover:bg-slate-800/30">
                      <td className="py-2 px-3 font-semibold text-white">{row.name}</td>
                      <td className="py-2 px-3 font-mono text-teal-400"><code>{row.key}</code></td>
                      <td className="py-2 px-3 font-mono font-bold text-white">
                        {row.val} {row.unit}
                      </td>
                      <td className="py-2 px-3 text-slate-400 font-mono text-[11px]">{row.ref}</td>
                      <td className="py-2 px-3">
                        <span
                          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold ${
                            row.ok
                              ? "bg-emerald-500/10 text-emerald-300 border border-emerald-500/20"
                              : "bg-amber-500/10 text-amber-300 border border-amber-500/20"
                          }`}
                        >
                          {row.ok ? "Within range" : "Out of reference"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Parameter Deltas when comparing custom scenario against baseline */}
          {scenarioComparison?.has_scenario && scenarioComparison.deltas && scenarioComparison.deltas.length > 0 && (
            <div className="space-y-3 pt-3 border-t border-teal-900/40">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold text-cyan-300 uppercase tracking-wider flex items-center gap-1.5">
                  <GitCompare className="w-3.5 h-3.5 text-cyan-400" />
                  What-if Parameter Deltas vs. Reference Baseline
                </h4>
              </div>

              <div className="overflow-x-auto rounded-xl border border-slate-800">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-900 text-slate-400 uppercase text-[10px] tracking-wider font-semibold">
                    <tr>
                      <th className="py-2 px-3">Parameter</th>
                      <th className="py-2 px-3">Baseline</th>
                      <th className="py-2 px-3">What-If Value</th>
                      <th className="py-2 px-3">Absolute Delta (&Delta;)</th>
                      <th className="py-2 px-3">% Change</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800 text-slate-300">
                    {scenarioComparison.deltas.map((d, index) => (
                      <tr key={`${d.field_name ?? "unknown-delta"}-${index}`} className="hover:bg-slate-800/30">
                        <td className="py-2 px-3 font-semibold text-white">
                          {d.display_name} (<code>{d.field_name}</code>)
                        </td>
                        <td className="py-2 px-3 font-mono text-slate-400">
                          {d.baseline_value} {d.unit}
                        </td>
                        <td className="py-2 px-3 font-mono font-bold text-cyan-300">
                          {d.scenario_value} {d.unit}
                        </td>
                        <td className="py-2 px-3 font-mono font-bold">
                          <span
                            className={
                              d.absolute_change > 0
                                ? "text-cyan-400"
                                : d.absolute_change < 0
                                ? "text-rose-400"
                                : "text-slate-400"
                            }
                          >
                            {d.absolute_change > 0 ? "+" : ""}
                            {d.absolute_change.toFixed(2)} {d.unit}
                          </span>
                        </td>
                        <td className="py-2 px-3 font-mono font-semibold">
                          {d.percent_change !== null ? (
                            <span
                              className={
                                d.percent_change > 0
                                  ? "text-cyan-400"
                                  : d.percent_change < 0
                                  ? "text-rose-400"
                                  : "text-slate-400"
                              }
                            >
                              {d.percent_change > 0 ? "+" : ""}
                              {d.percent_change.toFixed(1)}%
                            </span>
                          ) : (
                            "—"
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* SUBSECTION E: Temporary Session Scenario History */}
      {sessionScenarios.length > 0 && (
        <div className="rounded-2xl border border-slate-800 bg-[#0a1222]/90 p-5 shadow-xl space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <GitCompare className="w-4 h-4 text-teal-400" />
              Session Scenario History ({sessionScenarios.length} executed)
            </h3>
            <button
              type="button"
              onClick={onClearHistory}
              disabled={isLoading}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-rose-300 bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 transition-all cursor-pointer"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>Clear History</span>
            </button>
          </div>

          <div className="overflow-x-auto rounded-xl border border-slate-800">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900 text-slate-400 uppercase text-[10px] tracking-wider font-semibold">
                <tr>
                  <th className="py-2 px-3">Scenario Name</th>
                  <th className="py-2 px-3">Type</th>
                  <th className="py-2 px-3">Preset Base</th>
                  <th className="py-2 px-3">HR</th>
                  <th className="py-2 px-3">Contract</th>
                  <th className="py-2 px-3">Resist</th>
                  <th className="py-2 px-3">Compl</th>
                  <th className="py-2 px-3">Sim CO</th>
                  <th className="py-2 px-3">Sim EF</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 text-slate-300">
                {sessionScenarios.map((s, index) => (
                  <tr key={`${s.scenario_id ?? "unknown-scenario"}-${index}`} className="hover:bg-slate-800/30">
                    <td className="py-2 px-3 font-semibold text-white">{s.name}</td>
                    <td className="py-2 px-3">
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                        {s.kind}
                      </span>
                    </td>
                    <td className="py-2 px-3 text-slate-300">{s.preset}</td>
                    <td className="py-2 px-3 font-mono">{s.parameters.hr}</td>
                    <td className="py-2 px-3 font-mono">{s.parameters.contract}%</td>
                    <td className="py-2 px-3 font-mono">{s.parameters.resist}</td>
                    <td className="py-2 px-3 font-mono">{s.parameters.compl}</td>
                    <td className="py-2 px-3 font-mono font-bold text-teal-300">
                      {s.metrics ? `${s.metrics.co.toFixed(2)} L/min` : "—"}
                    </td>
                    <td className="py-2 px-3 font-mono font-bold text-cyan-300">
                      {s.metrics ? `${s.metrics.ef.toFixed(1)}%` : "—"}
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

