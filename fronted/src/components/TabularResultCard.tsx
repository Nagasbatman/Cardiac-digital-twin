"use client";

import React from "react";
import { HeartTabularResponse } from "@/types/heart_tabular";
import {
  ShieldAlert,
  ShieldCheck,
  Activity,
  AlertCircle,
  HelpCircle,
  TrendingUp,
  ArrowRight,
  Info,
  CheckCircle2,
} from "lucide-react";

interface TabularResultCardProps {
  result: HeartTabularResponse;
}

export const TabularResultCard: React.FC<TabularResultCardProps> = ({ result }) => {
  const isHighRisk = result.label === "High Risk";
  const isMediumRisk = result.label === "Medium Risk";
  const isLowRisk = result.label === "Low Risk";
  const isReview = result.status === "review";

  const probPercent =
    result.probability !== null && result.probability !== undefined
      ? (result.probability * 100).toFixed(1)
      : null;

  const thresholdPercent = (result.threshold * 100).toFixed(1);

  return (
    <div
      id="tabular-result-card"
      className="p-6 md:p-8 rounded-2xl bg-slate-900/90 border border-slate-800 shadow-2xl space-y-6 relative overflow-hidden"
    >
      {/* Background ambient glow based on risk */}
      <div
        className={`absolute -top-24 -right-24 w-72 h-72 rounded-full blur-3xl -z-10 pointer-events-none opacity-20 ${
          isHighRisk
            ? "bg-rose-500"
            : isMediumRisk
            ? "bg-amber-500"
            : isLowRisk
            ? "bg-emerald-500"
            : "bg-purple-500"
        }`}
      />

      {/* Header & Status Badge */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-slate-800">
        <div>
          <span className="text-[11px] uppercase tracking-wider font-semibold text-slate-400">
            Model II Evaluation Result
          </span>
          <h2 className="text-xl md:text-2xl font-bold text-white flex items-center gap-2 mt-1">
            <Activity className="w-6 h-6 text-rose-400" />
            <span>Cardiovascular Risk Assessment</span>
          </h2>
        </div>

        <div>
          {isReview ? (
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-purple-500/15 border border-purple-500/30 text-purple-300 font-semibold text-sm">
              <ShieldAlert className="w-4 h-4 text-purple-400" />
              <span>Review Needed (Anomaly Flagged)</span>
            </div>
          ) : isHighRisk ? (
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-rose-500/20 border border-rose-500/40 text-rose-300 font-semibold text-sm shadow-lg shadow-rose-950/40">
              <ShieldAlert className="w-4 h-4 text-rose-400 animate-pulse" />
              <span>High Risk (≥ 50%)</span>
            </div>
          ) : isMediumRisk ? (
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-amber-500/20 border border-amber-500/40 text-amber-300 font-semibold text-sm shadow-lg shadow-amber-950/40">
              <AlertCircle className="w-4 h-4 text-amber-400" />
              <span>Medium Risk (20.0% – 50%)</span>
            </div>
          ) : (
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 font-semibold text-sm shadow-lg shadow-emerald-950/40">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span>Low Risk (&lt; 20.0%)</span>
            </div>
          )}
        </div>
      </div>

      {/* Main Metric Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Calibrated Probability Card */}
        <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-3">
          <div className="text-xs text-slate-400 font-medium">Model Probability</div>
          <div className="flex items-baseline gap-2">
            <span
              className={`text-3xl font-extrabold ${
                isHighRisk
                  ? "text-rose-400"
                  : isMediumRisk
                  ? "text-amber-400"
                  : isLowRisk
                  ? "text-emerald-400"
                  : "text-slate-300"
              }`}
            >
              {probPercent !== null ? `${probPercent}%` : "N/A"}
            </span>
            <span className="text-xs text-slate-400">calibrated</span>
          </div>

          {/* Probability Bar */}
          {probPercent !== null && (
            <div className="space-y-1">
              <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden relative">
                <div
                  className={`h-full rounded-full transition-all duration-700 ${
                    isHighRisk
                      ? "bg-gradient-to-r from-amber-500 to-rose-500"
                      : isMediumRisk
                      ? "bg-amber-400"
                      : "bg-emerald-400"
                  }`}
                  style={{ width: `${Math.min(100, Math.max(0, parseFloat(probPercent)))}%` }}
                />
              </div>
              <div className="flex justify-between text-[10px] text-slate-500">
                <span>0%</span>
                <span className="text-cyan-400">Threshold: {thresholdPercent}%</span>
                <span>100%</span>
              </div>
            </div>
          )}
        </div>

        {/* Clinical Decision Threshold Card */}
        <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-2">
          <div className="text-xs text-slate-400 font-medium">Cost-Optimal Threshold</div>
          <div className="text-2xl font-bold text-cyan-400 font-mono">
            {thresholdPercent}%
          </div>
          <p className="text-[11px] text-slate-400 leading-tight">
            Tuned with a 5× cost penalty for missed cardiovascular cases (False Negatives) to prioritize patient safety.
          </p>
        </div>

        {/* Anomaly Gate Status */}
        <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-2">
          <div className="text-xs text-slate-400 font-medium">Stage 1 Anomaly Gate</div>
          <div className="flex items-center gap-2">
            {isReview ? (
              <>
                <AlertCircle className="w-5 h-5 text-purple-400" />
                <span className="text-sm font-semibold text-purple-300">Outlier / Atypical</span>
              </>
            ) : (
              <>
                <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                <span className="text-sm font-semibold text-emerald-300">Plausible Profile (Passed)</span>
              </>
            )}
          </div>
          <p className="text-[11px] text-slate-400 leading-tight">
            Isolation Forest (1% contamination) validates consistency with the CDC NHANES reference population.
          </p>
        </div>
      </div>

      {/* Model Recommendation Banner */}
      <div className="p-4 rounded-xl bg-gradient-to-r from-slate-950 via-slate-900 to-slate-950 border border-slate-800 flex items-start gap-3">
        <Info className="w-5 h-5 text-cyan-400 shrink-0 mt-0.5" />
        <div>
          <div className="text-xs font-semibold uppercase tracking-wider text-cyan-400">
            Model Recommendation
          </div>
          <p className="text-sm text-slate-200 mt-0.5 font-medium">{result.message}</p>
        </div>
      </div>

      {/* Contributing Factors Section */}
      {result.factors && result.factors.length > 0 && (
        <div className="space-y-3 pt-2">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-cyan-400" />
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300">
              Top Influencing Clinical Factors (vs Reference Population)
            </h3>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            {result.factors.map((factor, idx) => (
              <div
                key={idx}
                className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80 text-xs flex items-center justify-between"
              >
                <div>
                  <span className="font-semibold text-white capitalize">
                    {factor.feature.replace(/_/g, " ")}
                  </span>
                  <div className="text-[11px] text-slate-400 mt-0.5">
                    Patient: <span className="text-cyan-300 font-medium">{String(factor.patient_value)}</span>
                    {factor.reference_value !== undefined && (
                      <span className="text-slate-500"> (typical: {String(factor.reference_value)})</span>
                    )}
                  </div>
                </div>

                {factor.impact && (
                  <span
                    className={`font-mono text-xs px-2 py-0.5 rounded font-semibold ${
                      factor.impact.startsWith("+")
                        ? "bg-rose-500/15 text-rose-300 border border-rose-500/30"
                        : "bg-emerald-500/15 text-emerald-300 border border-emerald-500/30"
                    }`}
                  >
                    {factor.impact}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Research Disclaimer */}
      <div className="pt-4 border-t border-slate-800 text-[11px] text-slate-400 space-y-1">
        <p>
          <strong className="text-slate-300">Research & Investigational Notice:</strong> This prediction is generated by a machine-learning research model trained on the CDC NHANES 2007–March 2020 cohort (adults aged 40+, 12.5% prevalence). It is provided strictly for academic and experimental demonstration and does not constitute medical advice, diagnosis, or clinical guidance.
        </p>
      </div>
    </div>
  );
};

