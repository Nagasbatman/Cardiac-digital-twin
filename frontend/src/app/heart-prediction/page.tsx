"use client";

import React, { useState } from "react";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { TabularPredictionForm } from "@/components/TabularPredictionForm";
import { TabularResultCard } from "@/components/TabularResultCard";
import { predictHeartTabular, fetchHeartTabularSample } from "@/config/api";
import { HeartTabularInput, HeartTabularResponse } from "@/types/heart_tabular";
import {
  Activity,
  AlertCircle,
  FileSpreadsheet,
  CheckCircle2,
  Info,
  ShieldCheck,
  Stethoscope,
} from "lucide-react";

export default function HeartPredictionPage() {
  const [formData, setFormData] = useState<Partial<HeartTabularInput>>({});
  const [result, setResult] = useState<HeartTabularResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [sampleLoading, setSampleLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleFieldChange = (field: keyof HeartTabularInput, value: any) => {
    setFormData((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleLoadSample = async () => {
    setSampleLoading(true);
    setErrorMessage(null);
    try {
      const sample = await fetchHeartTabularSample();
      setFormData(sample);
    } catch (err: any) {
      console.error(err);
      setErrorMessage(
        err.message || "Failed to load sample patient. Please verify the Python API backend on port 8000."
      );
    } finally {
      setSampleLoading(false);
    }
  };

  const handleReset = () => {
    setFormData({});
    setResult(null);
    setErrorMessage(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setErrorMessage(null);

    try {
      const response = await predictHeartTabular(formData as HeartTabularInput);
      setResult(response);

      // Smooth scroll to results
      setTimeout(() => {
        document.getElementById("tabular-result-card")?.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      }, 150);
    } catch (err: any) {
      console.error(err);
      setErrorMessage(
        err.message ||
          "An error occurred while generating prediction. Ensure all 31 clinical parameters are provided and within physiological limits."
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#070b14] text-slate-100 flex flex-col font-sans">
      <Header />

      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 md:py-12 w-full space-y-8">
        {/* Page Hero Header */}
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
              <Activity className="w-3.5 h-3.5" />
              Module II
            </span>
            <span className="text-xs text-slate-400">
              CDC NHANES 2007–March 2020 Clinical Cohort (40+ Adults)
            </span>
          </div>

          <h1 className="text-2xl sm:text-3xl md:text-4xl font-extrabold text-white tracking-tight">
            Tabular Cardiovascular Disease Prediction
          </h1>
          <p className="text-sm sm:text-base text-slate-400 max-w-3xl leading-relaxed">
            Enter patient clinical parameters to obtain a model-based cardiovascular disease classification.
            Evaluated via a two-stage cascade: Isolation Forest anomaly screening followed by calibrated Logistic Regression inference.
          </p>
        </div>

        {/* Error Notification */}
        {errorMessage && (
          <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800/80 text-rose-300 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            <div className="text-xs sm:text-sm">
              <strong className="font-semibold">Validation / Inference Error: </strong>
              <span>{errorMessage}</span>
            </div>
          </div>
        )}

        {/* Input Form */}
        <TabularPredictionForm
          formData={formData}
          onChange={handleFieldChange}
          onSubmit={handleSubmit}
          onReset={handleReset}
          onLoadSample={handleLoadSample}
          isLoading={isLoading}
          sampleLoading={sampleLoading}
        />

        {/* Results Section */}
        {result && <TabularResultCard result={result} />}
      </main>

      <Footer />
    </div>
  );
}

