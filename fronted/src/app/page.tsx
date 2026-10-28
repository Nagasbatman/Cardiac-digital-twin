"use client";

import React, { useState } from "react";
import { Header } from "@/components/Header";
import { UploadSection } from "@/components/UploadSection";
import { SegmentationViewer } from "@/components/SegmentationViewer";
import { DiagnosisCard } from "@/components/DiagnosisCard";
import { BiomarkersTable } from "@/components/BiomarkersTable";
import { Footer } from "@/components/Footer";
import { submitAnalysis } from "@/config/api";
import { AnalysisResponse } from "@/types/cardiac";
import {
  Heart,
  Activity,
  AlertCircle,
  CheckCircle2,
  Sparkles,
  Info,
  Clock,
  Layers,
  FileText,
  ScanLine,
  FolderOpen,
  RefreshCcw,
  ShieldAlert,
  ArrowRight,
} from "lucide-react";

/** Classify the raw error string from the API into a known category. */
function classifyError(msg: string): "spatial_mismatch" | "mask_rejection" | "patient_mismatch" | "not_found" | "server_offline" | "general" {
  const m = msg.toLowerCase();
  if (m.includes("spatial") || m.includes("dimension mismatch") || m.includes("shape") || m.includes("mismatch"))
    return "spatial_mismatch";
  if (m.includes("ground-truth") || m.includes("segmentation mask") || m.includes("label map") || m.includes("rejected"))
    return "mask_rejection";
  if (m.includes("patient id") || m.includes("patient identity"))
    return "patient_mismatch";
  if (m.includes("not found") || m.includes("404"))
    return "not_found";
  if (m.includes("failed to fetch") || m.includes("network") || m.includes("port 8000") || m.includes("econnrefused"))
    return "server_offline";
  return "general";
}

export default function Home() {
  const [result, setResult] = useState<AnalysisResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [sampleLoading, setSampleLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [loadingStage, setLoadingStage] = useState<string>("");

  const runPipeline = async (formData: FormData) => {
    setIsLoading(true);
    setErrorMessage(null);
    setLoadingStage("Reading NIfTI cardiac volume & validating dimensions...");

    const stageTimer1 = setTimeout(() => {
      setLoadingStage("Inferring 4-Fold ViT-B/14 DPT Ensemble (folds 0–3 with TTA)...");
    }, 1500);

    const stageTimer2 = setTimeout(() => {
      setLoadingStage("Extracting 23 clinical biomarkers (volumes, mass, wall thickness)...");
    }, 4500);

    const stageTimer3 = setTimeout(() => {
      setLoadingStage("Evaluating 10-seed Random Forest classifier across 5 ACDC classes...");
    }, 6500);

    try {
      const data = await submitAnalysis(formData);
      setResult(data);
      // Smooth scroll to results
      setTimeout(() => {
        document.getElementById("results-dashboard")?.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      }, 200);
    } catch (err: any) {
      console.error(err);
      setErrorMessage(
        err.message ||
          "An error occurred while running the cardiac segmentation pipeline. Please verify the Python API server is running on port 8000."
      );
    } finally {
      clearTimeout(stageTimer1);
      clearTimeout(stageTimer2);
      clearTimeout(stageTimer3);
      setIsLoading(false);
      setSampleLoading(false);
      setLoadingStage("");
    }
  };

  const handleAnalyze = (formData: FormData) => {
    runPipeline(formData);
  };

  const handleLoadSample = () => {
    setSampleLoading(true);
    const fd = new FormData();
    fd.append("mode", "sample");
    fd.append("tta_enabled", "true");
    fd.append("height_cm", "169.0");
    fd.append("weight_kg", "79.0");
    runPipeline(fd);
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#070b14] text-slate-100">
      {/* Navigation Header */}
      <Header />

      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Hero Section */}
        <div className="space-y-3">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-950/60 border border-cyan-800/60 text-xs text-cyan-300 font-medium">
            <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
            <span>Unified Deep Learning & Clinical Biomarker Platform</span>
          </div>

          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white">
            Cardiac Digital Twin{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-blue-400 to-indigo-400">
              Diagnostic Portal
            </span>
          </h1>

          <p className="text-sm sm:text-base text-slate-400 max-w-3xl leading-relaxed">
            Execute 4-fold deep ensemble segmentation (RV, Myocardium, LV), extract 23 physiological biomarkers,
            and classify cardiomyopathy across 5 ACDC categories (NOR, DCM, HCM, MINF, RV) directly from short-axis MRI studies.
          </p>
        </div>

        {/* Error Alert Banner — smart per-error-type rendering */}
        {errorMessage && (() => {
          const kind = classifyError(errorMessage);

          if (kind === "spatial_mismatch") {
            // Parse shapes from messages like:
            //   "Spatial mismatch: ED shape (216, 256, 8) != ES shape (162, 208, 19)"
            //   "Spatial dimension mismatch: ED volume shape (216, 256, 8) conflicts with..."
            const shapeMatch = errorMessage.match(/\(([\d, ]+)\)[^(]*\(([\d, ]+)\)/);
            const edShape = shapeMatch ? shapeMatch[1] : null;
            const esShape = shapeMatch ? shapeMatch[2] : null;

            return (
              <div className="rounded-2xl border border-amber-600/40 bg-amber-950/30 overflow-hidden">
                {/* Header */}
                <div className="flex items-center gap-3 px-5 py-3.5 bg-amber-950/50 border-b border-amber-700/30">
                  <ShieldAlert className="w-5 h-5 text-amber-400 flex-shrink-0" />
                  <div>
                    <p className="text-sm font-bold text-amber-300">Spatial Dimension Mismatch — Input Rejected</p>
                    <p className="text-[11px] text-amber-500/80">
                      ED and ES volumes must come from the same acquisition session and share identical dimensions.
                    </p>
                  </div>
                </div>

                <div className="p-5 space-y-4">
                  {/* Shape comparison */}
                  {edShape && esShape && (
                    <div className="grid grid-cols-2 gap-3">
                      <div className="rounded-xl bg-cyan-950/40 border border-cyan-800/40 p-3 text-center">
                        <p className="text-[10px] font-semibold text-cyan-400 uppercase tracking-wider mb-1">End-Diastole (ED)</p>
                        <p className="font-mono text-base font-bold text-white">({edShape})</p>
                        <p className="text-[10px] text-slate-400 mt-0.5">H × W × Slices</p>
                      </div>
                      <div className="rounded-xl bg-rose-950/40 border border-rose-800/40 p-3 text-center">
                        <p className="text-[10px] font-semibold text-rose-400 uppercase tracking-wider mb-1">End-Systole (ES)</p>
                        <p className="font-mono text-base font-bold text-white">({esShape})</p>
                        <p className="text-[10px] text-slate-400 mt-0.5">H × W × Slices</p>
                      </div>
                    </div>
                  )}

                  {/* Explanation */}
                  <div className="rounded-xl bg-slate-900/60 border border-slate-700/50 p-4 space-y-3 text-xs">
                    <p className="font-semibold text-slate-200 flex items-center gap-1.5">
                      <Info className="w-3.5 h-3.5 text-cyan-400" /> Why does this happen?
                    </p>
                    <ul className="space-y-1.5 text-slate-400 pl-1">
                      <li className="flex items-start gap-2">
                        <ArrowRight className="w-3 h-3 text-amber-400 flex-shrink-0 mt-0.5" />
                        <span>Different dimensions show these files are incompatible, but do not identify whether the cause is the patient, scan session, or acquisition settings.</span>
                      </li>
                      <li className="flex items-start gap-2">
                        <ArrowRight className="w-3 h-3 text-amber-400 flex-shrink-0 mt-0.5" />
                        <span>The files have different FOV, resolution, or acquisition matrix. Both must be extracted from the <strong className="text-slate-200">same 4D cine or same DICOM series</strong>.</span>
                      </li>
                    </ul>
                  </div>

                  {/* Fix options */}
                  <div className="space-y-2">
                    <p className="text-[11px] font-semibold text-slate-300 uppercase tracking-wider">How to fix:</p>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-[11px]">
                      <div className="rounded-lg bg-slate-900/80 border border-slate-700 p-3 space-y-1">
                        <p className="font-semibold text-cyan-300 flex items-center gap-1.5"><ScanLine className="w-3.5 h-3.5" /> Option 1: Use 4D Cine</p>
                        <p className="text-slate-400">Switch to the <strong className="text-slate-300">"4D Cine Cardiac MRI"</strong> tab and upload the full 4-D temporal volume. Select ED and ES frame indices manually.</p>
                      </div>
                      <div className="rounded-lg bg-slate-900/80 border border-slate-700 p-3 space-y-1">
                        <p className="font-semibold text-emerald-300 flex items-center gap-1.5"><FolderOpen className="w-3.5 h-3.5" /> Option 2: Correct Paired Files</p>
                        <p className="text-slate-400">In the ACDC dataset, use <code className="text-cyan-400">patientXXX_frameED.nii</code> and <code className="text-cyan-400">patientXXX_frameES.nii</code> from the <strong className="text-slate-300">same patient folder</strong>.</p>
                      </div>
                      <div className="rounded-lg bg-slate-900/80 border border-slate-700 p-3 space-y-1">
                        <p className="font-semibold text-amber-300 flex items-center gap-1.5"><Sparkles className="w-3.5 h-3.5" /> Option 3: Run Demo</p>
                        <p className="text-slate-400">Click <strong className="text-slate-300">"Demo: Load Patient 101"</strong> to test the pipeline with the bundled DCM case immediately.</p>
                      </div>
                    </div>
                  </div>

                  <button
                    onClick={() => setErrorMessage(null)}
                    className="flex items-center gap-1.5 text-[11px] text-slate-400 hover:text-white transition"
                  >
                    <RefreshCcw className="w-3 h-3" /> Dismiss and try again
                  </button>
                </div>
              </div>
            );
          }

          if (kind === "mask_rejection") {
            return (
              <div className="p-4 rounded-xl bg-orange-950/40 border border-orange-600/50 flex items-start gap-3 text-orange-200 text-xs">
                <ShieldAlert className="w-5 h-5 text-orange-400 flex-shrink-0 mt-0.5" />
                <div className="space-y-1.5">
                  <p className="font-bold text-orange-300">Ground-Truth Segmentation Mask Rejected</p>
                  <p className="text-slate-300">{errorMessage}</p>
                  <p className="text-[11px] text-slate-400">
                    Upload a <strong className="text-slate-200">raw anatomical MRI acquisition</strong> — not a <code className="text-orange-300">_gt.nii</code> or <code className="text-orange-300">_seg.nii</code> label map.
                    In ACDC, use <code className="text-cyan-400">patientXXX_frameYY.nii</code> (no <code className="text-orange-400">_gt</code> suffix).
                  </p>
                  <button onClick={() => setErrorMessage(null)} className="flex items-center gap-1 text-[10px] text-slate-500 hover:text-white transition mt-1">
                    <RefreshCcw className="w-3 h-3" /> Dismiss
                  </button>
                </div>
              </div>
            );
          }

          if (kind === "patient_mismatch") {
            return (
              <div className="p-4 rounded-xl bg-purple-950/40 border border-purple-600/50 flex items-start gap-3 text-purple-200 text-xs">
                <AlertCircle className="w-5 h-5 text-purple-400 flex-shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <p className="font-bold text-purple-300">Patient ID Mismatch</p>
                  <p className="text-slate-300">{errorMessage}</p>
                  <p className="text-[11px] text-slate-400">Ensure ED and ES volumes are from the same patient. Patient identifiers embedded in filenames or headers do not match.</p>
                  <button onClick={() => setErrorMessage(null)} className="flex items-center gap-1 text-[10px] text-slate-500 hover:text-white transition mt-1">
                    <RefreshCcw className="w-3 h-3" /> Dismiss
                  </button>
                </div>
              </div>
            );
          }

          if (kind === "server_offline") {
            return (
              <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-600/50 flex items-start gap-3 text-rose-200 text-xs">
                <AlertCircle className="w-5 h-5 text-rose-400 flex-shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <p className="font-bold text-rose-300">API Server Unreachable</p>
                  <p className="text-slate-300">Cannot connect to the PULSE backend on port 8000.</p>
                  <p className="text-[11px] text-slate-400 font-mono bg-slate-900 inline-block px-2 py-1 rounded mt-1">
                    cd PULSE &amp;&amp; .venv\Scripts\python.exe api_server.py
                  </p>
                  <button onClick={() => setErrorMessage(null)} className="flex items-center gap-1 text-[10px] text-slate-500 hover:text-white transition mt-1">
                    <RefreshCcw className="w-3 h-3" /> Dismiss
                  </button>
                </div>
              </div>
            );
          }

          // General / fallback
          return (
            <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-600/50 flex items-start gap-3 text-rose-200 text-xs">
              <AlertCircle className="w-5 h-5 text-rose-400 flex-shrink-0 mt-0.5" />
              <div className="space-y-1">
                <p className="font-semibold text-rose-300">Pipeline Validation Error</p>
                <p className="text-slate-300">{errorMessage}</p>
                <p className="text-[11px] text-slate-400 pt-1">
                  Ensure the Python API server is running: <code className="text-cyan-400 bg-slate-900 px-1 py-0.5 rounded font-mono">python api_server.py</code>
                </p>
                <button onClick={() => setErrorMessage(null)} className="flex items-center gap-1 text-[10px] text-slate-500 hover:text-white transition mt-1">
                  <RefreshCcw className="w-3 h-3" /> Dismiss
                </button>
              </div>
            </div>
          );
        })()}

        {/* Upload and Configuration Panel */}
        <section>
          <UploadSection
            onAnalyze={handleAnalyze}
            isLoading={isLoading}
            onLoadSample={handleLoadSample}
            sampleLoading={sampleLoading}
          />
        </section>

        {/* In-Flight Multi-Stage Loading Indicator */}
        {isLoading && (
          <section className="glass-panel p-8 text-center space-y-5 glow-active">
            <div className="relative w-16 h-16 mx-auto flex items-center justify-center">
              <div className="absolute inset-0 rounded-full bg-cyan-500/20 animate-ping" />
              <div className="w-12 h-12 rounded-full bg-gradient-to-tr from-cyan-600 to-blue-600 flex items-center justify-center text-white shadow-lg shadow-cyan-500/30">
                <Heart className="w-6 h-6 animate-heartbeat text-white" />
              </div>
            </div>

            <div className="space-y-2 max-w-md mx-auto">
              <h3 className="text-lg font-bold text-white">
                PULSE Ensemble Processing
              </h3>
              <p className="text-xs text-cyan-300 font-mono animate-pulse">
                {loadingStage}
              </p>
              <p className="text-[11px] text-slate-400">
                Evaluating DINOv2 ViT-B/14 checkpoints across folds 0–3 with 4-way flip test-time augmentation.
              </p>
            </div>

            {/* Pipeline Step Badges */}
            <div className="flex flex-wrap items-center justify-center gap-3 pt-2 text-xs">
              <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-900 border border-slate-800 text-slate-300">
                <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
                <span>NIfTI Loading</span>
              </div>
              <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-900 border border-slate-800 text-slate-300">
                <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
                <span>4-Fold Ensemble</span>
              </div>
              <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-900 border border-slate-800 text-slate-300">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <span>23 Biomarkers</span>
              </div>
              <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-900 border border-slate-800 text-slate-300">
                <span className="w-2 h-2 rounded-full bg-purple-400 animate-pulse" />
                <span>ACDC Classification</span>
              </div>
            </div>
          </section>
        )}

        {/* Results Dashboard */}
        {result && (
          <div id="results-dashboard" className="space-y-8 pt-4">
            {/* 1. Diagnosis Card */}
            <section>
              <DiagnosisCard diagnosis={result.diagnosis} metadata={result.metadata} />
            </section>

            {/* 2. Volumetric Slice Overlays with Slider */}
            <section>
              <SegmentationViewer
                slices={result.slices}
                metadata={result.metadata}
              />
            </section>

            {/* 3. Extracted Biomarkers Table */}
            <section>
              <BiomarkersTable biomarkers={result.biomarkers} />
            </section>
          </div>
        )}

        {/* Empty State Banner (When not analyzed yet and not loading) */}
        {!result && !isLoading && (
          <section className="glass-panel p-8 sm:p-12 text-center space-y-4 border-dashed">
            <div className="w-14 h-14 mx-auto rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-500">
              <Layers className="w-7 h-7 text-cyan-400/80" />
            </div>

            <div className="space-y-1.5 max-w-lg mx-auto">
              <h3 className="text-base font-bold text-white">
                Awaiting Cardiac MRI Study
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Upload paired End-Diastole (ED) and End-Systole (ES) short-axis NIfTI scans above, or test with the bundled ACDC sample case to inspect segmentations, clinical indices, and diagnostic predictions.
              </p>
            </div>

            <div className="pt-2">
              <button
                type="button"
                onClick={handleLoadSample}
                disabled={sampleLoading}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700 text-xs font-semibold text-cyan-300 transition"
              >
                <Sparkles className="w-4 h-4 text-cyan-400" />
                <span>Run Demo Test (Patient 101 · DCM)</span>
              </button>
            </div>
          </section>
        )}
      </main>

      {/* Research & Compliance Footer */}
      <Footer />
    </div>
  );
}
