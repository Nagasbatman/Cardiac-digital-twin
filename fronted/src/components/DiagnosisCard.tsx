"use client";

import React from "react";
import {
  Stethoscope,
  Activity,
  CheckCircle2,
  AlertTriangle,
  Info,
  ShieldCheck,
  Percent
} from "lucide-react";
import { DiagnosisInfo, AnalysisMetadata } from "@/types/cardiac";

interface DiagnosisCardProps {
  diagnosis: DiagnosisInfo;
  metadata?: AnalysisMetadata;
}

const CLASS_THEMES: Record<
  string,
  {
    bg: string;
    border: string;
    text: string;
    accent: string;
    barColor: string;
  }
> = {
  NOR: {
    bg: "bg-emerald-950/40",
    border: "border-emerald-600/40",
    text: "text-emerald-400",
    accent: "bg-emerald-500",
    barColor: "bg-gradient-to-r from-emerald-600 to-teal-400",
  },
  DCM: {
    bg: "bg-cyan-950/40",
    border: "border-cyan-600/40",
    text: "text-cyan-400",
    accent: "bg-cyan-500",
    barColor: "bg-gradient-to-r from-cyan-600 to-blue-400",
  },
  HCM: {
    bg: "bg-purple-950/40",
    border: "border-purple-600/40",
    text: "text-purple-400",
    accent: "bg-purple-500",
    barColor: "bg-gradient-to-r from-purple-600 to-pink-400",
  },
  MINF: {
    bg: "bg-rose-950/40",
    border: "border-rose-600/40",
    text: "text-rose-400",
    accent: "bg-rose-500",
    barColor: "bg-gradient-to-r from-rose-600 to-orange-400",
  },
  RV: {
    bg: "bg-amber-950/40",
    border: "border-amber-600/40",
    text: "text-amber-400",
    accent: "bg-amber-500",
    barColor: "bg-gradient-to-r from-amber-600 to-yellow-400",
  },
  UNKNOWN: {
    bg: "bg-slate-900/40",
    border: "border-slate-700",
    text: "text-slate-400",
    accent: "bg-slate-500",
    barColor: "bg-slate-600",
  },
};

const CLASS_DESCRIPTIONS: Record<string, string> = {
  NOR: "Normal cardiac ventricular morphology and function within physiological limits.",
  DCM: "Dilated Cardiomyopathy: Marked ventricular dilation with elevated EDV/ESV and reduced ejection fraction (LVEF < 40%).",
  HCM: "Hypertrophic Cardiomyopathy: Asymmetric or concentric myocardial wall thickening (> 15 mm) and elevated indexed mass (LVMi).",
  MINF: "Myocardial Infarction: Ischemic myocardial injury with regional wall akinesia/thinning and depressed systolic ejection fraction.",
  RV: "Abnormal Right Ventricle: Significant right ventricular enlargement (RVEDVi > 110 mL/m²) or right systolic impairment (RVEF < 40%).",
};

export const DiagnosisCard: React.FC<DiagnosisCardProps> = ({ diagnosis, metadata }) => {
  const theme =
    CLASS_THEMES[diagnosis.predicted_class] || CLASS_THEMES.UNKNOWN;

  const probs = diagnosis.probabilities || {
    NOR: 0,
    DCM: 0,
    HCM: 0,
    MINF: 0,
    RV: 0,
  };

  const aClasses = ["NOR", "DCM", "HCM", "MINF", "RV"];

  return (
    <div className="glass-panel p-5 sm:p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 pb-3 border-b border-slate-800">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-blue-950/60 border border-blue-800/40 text-blue-400">
            <Stethoscope className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-bold text-white">
              Cardiomyopathy Diagnosis Classification
            </h3>
            <p className="text-xs text-slate-400">
              ACDC 5-Class Categorization via 10-Seed Random Forest Ensemble
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {metadata?.verification_status && (
            <span
              className={`text-[11px] font-mono font-semibold px-2.5 py-0.5 rounded-full border ${
                metadata.verification_status === "metadata-verified"
                  ? "bg-emerald-950/70 border-emerald-500/40 text-emerald-300"
                  : "bg-amber-950/70 border-amber-500/40 text-amber-300"
              }`}
            >
              {metadata.verification_status === "metadata-verified"
                ? "✓ Metadata-Verified (Info.cfg)"
                : "⚡ User-Confirmed Phases"}
            </span>
          )}
          {metadata?.patient_id && (
            <span className="text-[11px] font-mono px-2 py-0.5 rounded-md bg-slate-900 border border-slate-800 text-slate-300">
              ID: {metadata.patient_id}
            </span>
          )}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-900 border border-slate-800 text-[11px] text-slate-400">
            <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />
            <span>Biomarker-Decoupled</span>
          </div>
        </div>
      </div>

      {/* Non-fatal Clinical Warnings Banner */}
      {metadata?.warnings && metadata.warnings.length > 0 && (
        <div className="p-3.5 rounded-xl bg-amber-950/30 border border-amber-600/40 space-y-1.5 text-xs text-amber-200">
          <div className="flex items-center gap-1.5 font-semibold text-amber-300">
            <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0" />
            <span>Clinical Verification Notices ({metadata.warnings.length}):</span>
          </div>
          <ul className="list-disc list-inside space-y-0.5 text-slate-300 text-[11px]">
            {metadata.warnings.map((w, idx) => (
              <li key={idx}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Main Prediction Banner */}
      <div
        className={`p-5 rounded-2xl border ${theme.border} ${theme.bg} relative overflow-hidden transition-all`}
      >
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Predicted ACDC Category
              </span>
              <span
                className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${theme.accent}/20 ${theme.text} border ${theme.border}`}
              >
                Primary Class
              </span>
            </div>
            <div className="flex items-baseline gap-3 flex-wrap">
              <h2 className={`text-2xl sm:text-3xl font-extrabold ${theme.text}`}>
                {diagnosis.predicted_class}
              </h2>
              <span className="text-lg font-semibold text-slate-200">
                — {diagnosis.predicted_full_name}
              </span>
            </div>
            <p className="text-xs text-slate-300 max-w-2xl pt-1">
              {CLASS_DESCRIPTIONS[diagnosis.predicted_class] ||
                diagnosis.description ||
                "Clinical biomarker pattern evaluated against ACDC criteria."}
            </p>
          </div>

          {/* Confidence Dial Badge */}
          <div className="flex flex-col items-end flex-shrink-0">
            <div className="text-right">
              <span className="text-[11px] text-slate-400 uppercase tracking-wider block">
                Model Confidence
              </span>
              <div className="flex items-center gap-1 font-mono text-2xl font-bold text-white">
                <span>{diagnosis.confidence.toFixed(1)}</span>
                <span className="text-sm text-cyan-400">%</span>
              </div>
            </div>
            <div className="w-24 h-2 bg-slate-800 rounded-full mt-1.5 overflow-hidden">
              <div
                className={`h-full ${theme.barColor} rounded-full transition-all duration-700`}
                style={{ width: `${Math.min(100, diagnosis.confidence)}%` }}
              />
            </div>
          </div>
        </div>

        {/* Diagnosis Technical Details */}
        {diagnosis.details && (
          <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-start gap-2 text-xs text-slate-400">
            <Info className="w-3.5 h-3.5 text-slate-500 flex-shrink-0 mt-0.5" />
            <span>{diagnosis.details}</span>
          </div>
        )}
      </div>

      {/* Class Probabilities Distribution */}
      <div className="space-y-3">
        <div className="flex items-center justify-between text-xs font-semibold text-slate-300">
          <span>Class Probability Distribution (5 ACDC Classes)</span>
          <span className="text-slate-500 font-mono text-[11px]">
            Sum = 100.0%
          </span>
        </div>

        <div className="space-y-2.5">
          {aClasses.map((cls) => {
            const prob = (probs[cls] || 0) * 100;
            const isWinner = cls === diagnosis.predicted_class;
            const clsTheme = CLASS_THEMES[cls] || CLASS_THEMES.UNKNOWN;

            return (
              <div
                key={cls}
                className={`p-2.5 rounded-xl border transition-all ${
                  isWinner
                    ? `${clsTheme.bg} ${clsTheme.border}`
                    : "bg-slate-900/40 border-slate-800/60 hover:border-slate-700"
                }`}
              >
                <div className="flex items-center justify-between text-xs mb-1.5">
                  <div className="flex items-center gap-2">
                    <span
                      className={`font-mono font-bold px-1.5 py-0.5 rounded text-[11px] ${
                        isWinner
                          ? `${clsTheme.accent} text-white`
                          : "bg-slate-800 text-slate-300"
                      }`}
                    >
                      {cls}
                    </span>
                    <span
                      className={`font-medium ${
                        isWinner ? clsTheme.text : "text-slate-300"
                      }`}
                    >
                      {cls === "NOR" && "Normal Heart"}
                      {cls === "DCM" && "Dilated Cardiomyopathy"}
                      {cls === "HCM" && "Hypertrophic Cardiomyopathy"}
                      {cls === "MINF" && "Myocardial Infarction"}
                      {cls === "RV" && "Abnormal Right Ventricle"}
                    </span>
                  </div>

                  <span
                    className={`font-mono font-semibold ${
                      isWinner ? clsTheme.text : "text-slate-400"
                    }`}
                  >
                    {prob.toFixed(1)}%
                  </span>
                </div>

                {/* Progress bar */}
                <div className="w-full h-1.5 bg-slate-800/80 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${
                      isWinner ? clsTheme.barColor : "bg-slate-600"
                    } rounded-full transition-all duration-700`}
                    style={{ width: `${Math.max(1, prob)}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
