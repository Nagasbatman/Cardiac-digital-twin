"use client";

import React from "react";
import { HeartTabularResponse } from "@/types/heart_tabular";
import {
  CheckCircle2,
  Download,
  Info,
  TrendingUp,
  TrendingDown,
  ArrowRight,
  AlertTriangle,
} from "lucide-react";

interface TabularResultCardProps {
  result: HeartTabularResponse;
}

const FEATURE_DISPLAY_NAMES: Record<string, string> = {
  age: "Age",
  gender: "Gender",
  ethnicity: "Ethnicity",
  education_level: "Education Level",
  poverty_income_ratio: "Poverty Income Ratio",
  bmi: "Body Mass Index (BMI)",
  waist_cm: "Waist Circumference",
  height_cm: "Height",
  systolic_bp: "Bp Systolic",
  diastolic_bp: "Bp Diastolic",
  resting_heart_rate: "Resting Heart Rate",
  total_cholesterol: "Total Cholesterol",
  hdl_cholesterol: "HDL Cholesterol",
  hba1c: "HbA1c",
  serum_creatinine: "Serum Creatinine",
  uric_acid: "Uric Acid",
  albumin_creatinine_ratio: "Albumin-to-Creatinine Ratio (ACR)",
  white_blood_cells: "White Blood Cells",
  hemoglobin: "Hemoglobin",
  rdw: "Red Cell Distribution Width (RDW)",
  smoking_status: "Smoking Status",
  physically_active: "Physically Active",
  hypertension_history: "Hypertension History",
  high_cholesterol_history: "High Cholesterol History",
  diabetes_status: "Diabetes",
  stroke_history: "Stroke History",
  family_history_chd: "Family History CHD",
  general_health: "General Health",
  chest_pain_type: "Chest Pain Type",
  severe_chest_pain: "Severe Chest Pain",
  sob_on_exertion: "Shortness of Breath (Exertion)",
  pulse_pressure: "Pulse Pressure",
  non_hdl_cholesterol: "Non-HDL Cholesterol",
  tc_hdl_ratio: "Total / HDL Ratio",
  waist_to_height_ratio: "Waist-to-Height Ratio",
  egfr: "eGFR",
  log_acr: "Log ACR",
  risk_factor_count: "Total Risk Factors",
};

export const TabularResultCard: React.FC<TabularResultCardProps> = ({ result }) => {
  const prob = result.probability ?? 0;
  const threshold = result.threshold ?? 0.2003;
  const probPercent = (prob * 100).toFixed(0);
  const thresholdPercent = (threshold * 100).toFixed(1);

  // Position on the continuum where halfway (50%) = threshold
  let continuumPercent = 0;
  if (prob <= threshold) {
    continuumPercent = threshold > 0 ? (prob / threshold) * 50 : 0;
  } else {
    continuumPercent = 50 + ((prob - threshold) / (1 - threshold)) * 50;
  }
  continuumPercent = Math.min(100, Math.max(0, continuumPercent));

  const isPositive = result.positive ?? prob >= threshold;
  const isHighRisk = result.label === "High Risk";
  const isMediumRisk = result.label === "Medium Risk";
  const isLowRisk = result.label === "Low Risk";
  const isReview = result.status === "review";

  const handleDownloadJson = () => {
    const dataStr =
      "data:text/json;charset=utf-8," +
      encodeURIComponent(JSON.stringify(result, null, 2));
    const downloadAnchor = document.createElement("a");
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute(
      "download",
      `heart_disease_prediction_${Date.now()}.json`
    );
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  return (
    <div
      id="tabular-result-card"
      className="p-6 sm:p-8 rounded-2xl bg-slate-900/80 text-white border border-slate-800 shadow-2xl space-y-6 font-sans transition-all"
    >
      {/* 1. Header Row */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-1">
        <div>
          <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
            SCREENING OUTPUT
          </div>
          <h2 className="text-xl sm:text-2xl font-extrabold text-white tracking-tight mt-0.5">
            Tabular Model Result
          </h2>
        </div>

        <div className="flex items-center gap-2.5">
          {/* Status Pill */}
          <div
            className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold ${
              isReview
                ? "bg-purple-500/15 text-purple-300 border border-purple-500/30"
                : isPositive
                ? "bg-amber-500/20 text-amber-300 border border-amber-500/40"
                : "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
            }`}
          >
            {isReview ? (
              <AlertTriangle className="w-3.5 h-3.5 text-purple-400" />
            ) : (
              <CheckCircle2
                className={`w-3.5 h-3.5 ${
                  isPositive ? "text-amber-400" : "text-emerald-400"
                }`}
              />
            )}
            <span>
              {isReview
                ? "Status: Review Required"
                : isPositive
                ? "Status: Screen Positive"
                : "Status: Screen Negative"}
            </span>
          </div>

          {/* Download JSON Button */}
          <button
            type="button"
            onClick={handleDownloadJson}
            className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 border border-slate-700 transition-colors shadow-sm cursor-pointer"
          >
            <Download className="w-3.5 h-3.5 text-slate-400" />
            <span>Download JSON</span>
          </button>
        </div>
      </div>

      {/* 2. Top 3 Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Card 1: Estimated Risk */}
        <div className="p-5 rounded-2xl bg-slate-950/80 border border-slate-800 shadow-sm flex flex-col justify-between">
          <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
            ESTIMATED CVD RISK
          </div>
          <div className="my-2">
            <span
              className={`text-4xl font-extrabold tracking-tight ${
                isReview
                  ? "text-purple-400"
                  : isHighRisk
                  ? "text-rose-400"
                  : isMediumRisk
                  ? "text-amber-400"
                  : "text-emerald-400"
              }`}
            >
              {result.probability !== null ? `${probPercent}%` : "Review"}
            </span>
          </div>
          <div className="text-xs text-slate-400 font-medium">
            Calibrated P(Disease)
          </div>
        </div>

        {/* Card 2: Decision Band */}
        <div className="p-5 rounded-2xl bg-slate-950/80 border border-slate-800 shadow-sm flex flex-col justify-between">
          <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
            DECISION BAND
          </div>
          <div className="my-2">
            <span className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              {isReview ? "Outlier (Review)" : result.label || "Indeterminate"}
            </span>
          </div>
          <div className="text-xs text-slate-400 font-medium">
            Threshold: {thresholdPercent}%
          </div>
        </div>

        {/* Card 3: Routing Action */}
        <div className="p-5 rounded-2xl bg-slate-950/80 border border-slate-800 shadow-sm flex flex-col justify-between">
          <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
            ROUTING ACTION
          </div>
          <div className="my-2">
            <div className="text-sm sm:text-base font-bold text-cyan-400 flex items-center gap-1.5">
              <span className="text-base">→</span>
              <span>
                {isReview
                  ? "Manual Clinical Review"
                  : isPositive
                  ? "Refer for Cardiology Work-up"
                  : "Routine Preventive Care"}
              </span>
            </div>
          </div>
          <div className="text-xs text-slate-400 font-medium">
            {isReview
              ? "Atypical clinical profile flagged"
              : isPositive
              ? "ECG + stress tests advised"
              : "Standard annual primary check-up"}
          </div>
        </div>
      </div>

      {/* 3. Risk Continuum Progress Bar */}
      <div className="space-y-1.5 pt-1">
        <div className="flex items-center justify-between text-xs sm:text-sm font-semibold text-slate-300">
          <span>Risk Continuum</span>
          <span>Routing Threshold: {thresholdPercent}%</span>
        </div>

        {/* The Bar with Halfway Divider */}
        <div className="relative w-full h-3.5 bg-slate-800 rounded-full overflow-hidden border border-slate-700">
          {/* Halfway Divider Line */}
          <div
            className="absolute top-0 bottom-0 w-0.5 bg-slate-600 z-20"
            style={{ left: "50%" }}
          />

          {/* Filled progress bar */}
          <div
            className="h-full rounded-full transition-all duration-700 bg-gradient-to-r from-[#e11d48] to-[#be123c]"
            style={{ width: `${continuumPercent}%` }}
          />
        </div>

        {/* Continuum Labels */}
        <div className="flex items-center justify-between text-[11px] text-slate-500 font-medium pt-0.5">
          <span>0% (Lowest Risk)</span>
          <span className="text-slate-300 font-semibold text-center">
            ▲ Halfway = Routing Threshold
          </span>
          <span>100% (High Risk)</span>
        </div>
      </div>

      {/* 4. Action Recommended Banner */}
      <div className="p-4 sm:p-5 rounded-xl bg-amber-500/10 border border-amber-500/20 shadow-sm">
        <div className="text-[11px] font-bold uppercase tracking-wider text-amber-400 mb-1">
          ACTION RECOMMENDED
        </div>
        <p className="text-sm sm:text-base font-medium text-amber-200 leading-relaxed">
          {result.message}
        </p>
      </div>

      {/* 5. What moved this patient's risk? Table */}
      <div className="space-y-3 pt-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 rounded-full bg-slate-800 flex items-center justify-center text-cyan-400">
              <Info className="w-4 h-4" />
            </div>
            <h3 className="text-sm sm:text-base font-bold text-white">
              What moved this patient's risk?
            </h3>
          </div>
          <span className="text-xs text-slate-400 font-medium">
            Top {result.factors?.length ?? 5} influence factors
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs sm:text-sm">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 font-semibold">
                <th className="py-2.5 pr-4">Biomarker / Feature</th>
                <th className="py-2.5 px-4">This Patient</th>
                <th className="py-2.5 px-4">Population Reference</th>
                <th className="py-2.5 pl-4 text-right">Risk Impact</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {result.factors && result.factors.length > 0 ? (
                result.factors.map((factor, idx) => {
                  const featureName =
                    FEATURE_DISPLAY_NAMES[factor.feature] ||
                    factor.feature
                      .replace(/_/g, " ")
                      .replace(/\b\w/g, (c) => c.toUpperCase());

                  const patientVal =
                    factor.value ?? factor.patient_value ?? "—";
                  const referenceVal =
                    factor.typical ?? factor.reference_value ?? "none";

                  // Format impact e.g. +25.6 pts
                  let impactStr = factor.impact;
                  let isPositiveEffect = true;
                  if (!impactStr && factor.effect !== undefined) {
                    const pts = factor.effect * 100;
                    isPositiveEffect = pts >= 0;
                    impactStr = `${pts >= 0 ? "+" : ""}${pts.toFixed(1)} pts`;
                  } else if (impactStr) {
                    isPositiveEffect = !impactStr.startsWith("-");
                  }

                  return (
                    <tr key={idx} className="hover:bg-slate-800/50 transition-colors">
                      <td className="py-3 pr-4 font-medium text-slate-200">
                        {featureName}
                      </td>
                      <td className="py-3 px-4 text-slate-200">
                        {String(patientVal)}
                      </td>
                      <td className="py-3 px-4 text-slate-400">
                        {String(referenceVal)}
                      </td>
                      <td className="py-3 pl-4 text-right">
                        <span
                          className={`font-semibold inline-flex items-center gap-1 ${
                            isPositiveEffect
                              ? "text-rose-400"
                              : "text-emerald-400"
                          }`}
                        >
                          {isPositiveEffect ? (
                            <TrendingUp className="w-3.5 h-3.5 inline text-rose-400" />
                          ) : (
                            <TrendingDown className="w-3.5 h-3.5 inline text-emerald-400" />
                          )}
                          <span>{impactStr}</span>
                        </span>
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={4} className="py-4 text-center text-slate-400">
                    No significant risk-shifting factors identified for this profile.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Methodology Footer Note */}
        <p className="text-[11px] text-slate-500 italic pt-2 leading-relaxed">
          Methodology: what-if: effect = probability for this patient - probability
          with this one value replaced by the typical training patient's (median, or
          most common answer)
        </p>
      </div>
    </div>
  );
};
