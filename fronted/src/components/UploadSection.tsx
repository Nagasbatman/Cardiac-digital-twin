"use client";

import React, { useState, useRef } from "react";
import {
  UploadCloud,
  FileCheck2,
  X,
  Play,
  RotateCcw,
  Sparkles,
  Info,
  Sliders,
  User,
  Layers,
  FileText
} from "lucide-react";

interface UploadSectionProps {
  onAnalyze: (formData: FormData) => void;
  isLoading: boolean;
  onLoadSample: () => void;
  sampleLoading: boolean;
}

function patientIdFromFilename(filename: string): string | null {
  const match = filename.match(/(?:^|[^a-z0-9])patient[_-]?0*(\d+)(?=[^0-9]|$)/i);
  return match ? `patient${Number(match[1])}` : null;
}

export const UploadSection: React.FC<UploadSectionProps> = ({
  onAnalyze,
  isLoading,
  onLoadSample,
  sampleLoading,
}) => {
  const [tab, setTab] = useState<"paired" | "cine4d">("paired");
  
  // Paired files
  const [edFile, setEdFile] = useState<File | null>(null);
  const [esFile, setEsFile] = useState<File | null>(null);
  const edPatientId = edFile ? patientIdFromFilename(edFile.name) : null;
  const esPatientId = esFile ? patientIdFromFilename(esFile.name) : null;
  const patientIdsConflict = Boolean(edPatientId && esPatientId && edPatientId !== esPatientId);

  // 4D Cine file & frames
  const [cineFile, setCineFile] = useState<File | null>(null);
  const [edFrame, setEdFrame] = useState<number>(1);
  const [esFrame, setEsFrame] = useState<number>(14);

  // Patient demographics
  const [heightCm, setHeightCm] = useState<number>(170);
  const [weightKg, setWeightKg] = useState<number>(70);
  const [ttaEnabled, setTtaEnabled] = useState<boolean>(true);
  const [showDemographics, setShowDemographics] = useState<boolean>(false);

  const edInputRef = useRef<HTMLInputElement>(null);
  const esInputRef = useRef<HTMLInputElement>(null);
  const cineInputRef = useRef<HTMLInputElement>(null);

  const [userConfirmed, setUserConfirmed] = useState<boolean>(true);

  // Real-time Dubois BSA preview
  const previewBsa = (
    0.007184 *
    Math.pow(heightCm || 170, 0.725) *
    Math.pow(weightKg || 70, 0.425)
  ).toFixed(2);

  const handleFileDrop = (
    e: React.DragEvent<HTMLDivElement>,
    target: "ed" | "es" | "cine"
  ) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (isValidNifti(file.name)) {
        if (file.name.toLowerCase().includes("_gt.") || file.name.toLowerCase().endsWith("_gt.nii") || file.name.toLowerCase().endsWith("_gt.nii.gz")) {
          alert("Ground-truth segmentation masks ('_gt') cannot be uploaded for MRI analysis. Please select a raw anatomical acquisition.");
          return;
        }
        if (target === "ed") setEdFile(file);
        if (target === "es") setEsFile(file);
        if (target === "cine") setCineFile(file);
      } else {
        alert("Please upload a valid NIfTI file (.nii or .nii.gz).");
      }
    }
  };

  const isValidNifti = (name: string) => {
    return name.endsWith(".nii") || name.endsWith(".nii.gz");
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!userConfirmed) {
      alert("Please confirm that the selected volumes or frame indices represent the intended End-Diastole and End-Systole phases before proceeding.");
      return;
    }

    if (tab === "paired") {
      if (!edFile && !esFile) {
        alert("Paired mode requires both End-Diastole (ED) and End-Systole (ES) volumes. Neither volume was provided.");
        return;
      }
      if (!edFile) {
        alert("Paired mode requires both ED and ES volumes. End-Diastole (ED) volume is missing.");
        return;
      }
      if (!esFile) {
        alert("Paired mode requires both ED and ES volumes. End-Systole (ES) volume is missing.");
        return;
      }
      if (edFile.name === esFile.name && edFile.size === esFile.size) {
        alert("Identical files provided for both ED and ES. End-diastole and end-systole represent distinct cardiac phases and require separate acquisitions.");
        return;
      }
      if (patientIdsConflict) {
        alert(`Patient IDs in the selected filenames do not match (${edPatientId} vs ${esPatientId}). Select ED and ES files for the same patient.`);
        return;
      }

      const fd = new FormData();
      fd.append("mode", "paired");
      fd.append("ed_file", edFile);
      fd.append("es_file", esFile);
      fd.append("height_cm", heightCm.toString());
      fd.append("weight_kg", weightKg.toString());
      fd.append("tta_enabled", ttaEnabled.toString());
      fd.append("user_confirmed", userConfirmed.toString());
      onAnalyze(fd);
    } else {
      if (!cineFile) {
        alert("Please upload a 4D Cine cardiac MRI volume.");
        return;
      }
      if (edFrame === esFrame) {
        alert("ED and ES frame indices cannot be identical. End-diastole (max volume) and end-systole (min volume) must represent distinct cardiac phases.");
        return;
      }
      if (edFrame < 1 || esFrame < 1) {
        alert("Frame indices must be positive integers (1 or greater).");
        return;
      }

      const fd = new FormData();
      fd.append("mode", "cine4d");
      fd.append("cine_file", cineFile);
      fd.append("ed_frame_idx", edFrame.toString());
      fd.append("es_frame_idx", esFrame.toString());
      fd.append("height_cm", heightCm.toString());
      fd.append("weight_kg", weightKg.toString());
      fd.append("tta_enabled", ttaEnabled.toString());
      fd.append("user_confirmed", userConfirmed.toString());
      onAnalyze(fd);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  return (
    <div className="glass-panel p-5 sm:p-6 space-y-6">
      {/* Tab Switcher */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
        <div className="flex p-1 bg-slate-900/90 rounded-xl border border-slate-800">
          <button
            type="button"
            onClick={() => setTab("paired")}
            className={`px-4 py-2 text-xs sm:text-sm font-medium rounded-lg transition-all ${
              tab === "paired"
                ? "bg-cyan-600 text-white shadow-md shadow-cyan-600/30"
                : "text-slate-400 hover:text-white"
            }`}
          >
            Paired ED & ES Volumes
          </button>
          <button
            type="button"
            onClick={() => setTab("cine4d")}
            className={`px-4 py-2 text-xs sm:text-sm font-medium rounded-lg transition-all ${
              tab === "cine4d"
                ? "bg-cyan-600 text-white shadow-md shadow-cyan-600/30"
                : "text-slate-400 hover:text-white"
            }`}
          >
            4D Cine Cardiac MRI
          </button>
        </div>

        {/* 1-Click Quick Sample Button */}
        <button
          type="button"
          onClick={onLoadSample}
          disabled={sampleLoading || isLoading}
          className="inline-flex items-center justify-center gap-1.5 px-3.5 py-2 text-xs font-semibold rounded-xl bg-gradient-to-r from-amber-500/10 via-amber-500/20 to-orange-500/10 text-amber-300 border border-amber-500/30 hover:border-amber-400 transition-all hover:shadow-[0_0_15px_rgba(245,158,11,0.2)] disabled:opacity-50"
        >
          <Sparkles className="w-3.5 h-3.5 text-amber-400" />
          <span>{sampleLoading ? "Loading Sample..." : "Demo: Load Patient 101 (DCM)"}</span>
        </button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        {tab === "paired" && (
          <div className="flex items-start gap-2.5 px-3.5 py-2.5 rounded-xl bg-cyan-950/25 border border-cyan-700/30 text-[11px] text-cyan-100">
            <Info className="w-3.5 h-3.5 text-cyan-400 flex-shrink-0 mt-0.5" />
            <span>
              Upload ED and ES volumes from the <strong className="text-white">same patient and same MRI acquisition</strong>. Their 3D dimensions (height, width, and slices) and voxel spacing must match. This is checked after upload; file size alone cannot confirm compatibility. For frames from one 4D scan, use the 4D Cine tab.
            </span>
          </div>
        )}
        {tab === "paired" && patientIdsConflict && (
          <div role="alert" className="flex items-start gap-2.5 px-3.5 py-2.5 rounded-xl bg-rose-950/30 border border-rose-700/40 text-[11px] text-rose-200">
            <Info className="w-3.5 h-3.5 text-rose-400 flex-shrink-0 mt-0.5" />
            <span>
              <strong className="text-rose-300">These files appear to be from different patients:</strong> ED is {edPatientId}; ES is {esPatientId}. Choose the matching ED or ES file from the same patient folder. The filename check is a hint; the server also validates patient identity from available metadata.
            </span>
          </div>
        )}
        {/* PAIRED MODE UPLOADERS */}
        {tab === "paired" && (
          <>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* ED File Dropzone */}
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => handleFileDrop(e, "ed")}
              className={`relative rounded-xl border-2 border-dashed p-4 text-center transition-all ${
                edFile
                  ? "border-emerald-500/50 bg-emerald-950/10"
                  : "border-slate-700/80 hover:border-cyan-500/60 bg-slate-900/40"
              }`}
            >
              <input
                ref={edInputRef}
                type="file"
                accept=".nii,.gz"
                className="hidden"
                onChange={(e) => {
                  if (e.target.files?.[0]) setEdFile(e.target.files[0]);
                }}
              />
              {edFile ? (
                <div className="flex items-center justify-between gap-2 p-2 bg-slate-900/80 rounded-lg border border-slate-700">
                  <div className="flex items-center gap-2 overflow-hidden text-left">
                    <FileCheck2 className="w-5 h-5 text-emerald-400 flex-shrink-0" />
                    <div className="overflow-hidden">
                      <p className="text-xs font-semibold text-white truncate">
                        {edFile.name}
                      </p>
                      <p className="text-[10px] text-slate-400">
                        {formatFileSize(edFile.size)} • End-Diastole
                      </p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setEdFile(null)}
                    className="p-1 hover:bg-slate-800 rounded text-slate-400 hover:text-rose-400 transition"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              ) : (
                <div
                  onClick={() => edInputRef.current?.click()}
                  className="cursor-pointer py-4 flex flex-col items-center justify-center space-y-2"
                >
                  <div className="w-10 h-10 rounded-full bg-cyan-950/60 border border-cyan-800/60 flex items-center justify-center text-cyan-400">
                    <UploadCloud className="w-5 h-5" />
                  </div>
                  <p className="text-xs font-semibold text-slate-200">
                    End-Diastole (ED) Volume
                  </p>
                  <p className="text-[11px] text-slate-400">
                    Drop <code className="text-cyan-400">.nii</code> or <code className="text-cyan-400">.nii.gz</code> here or click
                  </p>
                </div>
              )}
            </div>

            {/* ES File Dropzone */}
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => handleFileDrop(e, "es")}
              className={`relative rounded-xl border-2 border-dashed p-4 text-center transition-all ${
                esFile
                  ? "border-emerald-500/50 bg-emerald-950/10"
                  : "border-slate-700/80 hover:border-cyan-500/60 bg-slate-900/40"
              }`}
            >
              <input
                ref={esInputRef}
                type="file"
                accept=".nii,.gz"
                className="hidden"
                onChange={(e) => {
                  if (e.target.files?.[0]) setEsFile(e.target.files[0]);
                }}
              />
              {esFile ? (
                <div className="flex items-center justify-between gap-2 p-2 bg-slate-900/80 rounded-lg border border-slate-700">
                  <div className="flex items-center gap-2 overflow-hidden text-left">
                    <FileCheck2 className="w-5 h-5 text-emerald-400 flex-shrink-0" />
                    <div className="overflow-hidden">
                      <p className="text-xs font-semibold text-white truncate">
                        {esFile.name}
                      </p>
                      <p className="text-[10px] text-slate-400">
                        {formatFileSize(esFile.size)} • End-Systole
                      </p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setEsFile(null)}
                    className="p-1 hover:bg-slate-800 rounded text-slate-400 hover:text-rose-400 transition"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              ) : (
                <div
                  onClick={() => esInputRef.current?.click()}
                  className="cursor-pointer py-4 flex flex-col items-center justify-center space-y-2"
                >
                  <div className="w-10 h-10 rounded-full bg-blue-950/60 border border-blue-800/60 flex items-center justify-center text-blue-400">
                    <UploadCloud className="w-5 h-5" />
                  </div>
                  <p className="text-xs font-semibold text-slate-200">
                    End-Systole (ES) Volume
                  </p>
                  <p className="text-[11px] text-slate-400">
                    Drop <code className="text-blue-400">.nii</code> or <code className="text-blue-400">.nii.gz</code> here or click
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Paired-mode spatial requirement callout - visible when both files loaded */}
          {edFile && esFile && (
            <div className="flex items-start gap-2.5 px-3.5 py-2.5 rounded-xl bg-amber-950/25 border border-amber-700/30 text-[11px] text-amber-200">
              <Info className="w-3.5 h-3.5 text-amber-400 flex-shrink-0 mt-0.5" />
              <span>
                <strong className="text-amber-300">Same-acquisition requirement:</strong> ED and ES must originate from the{" "}
                <strong className="text-white">same 4D cine scan</strong> with identical matrix dimensions (H × W × Slices).
                If your scans have different slice counts or FOV, switch to the{" "}
                <button
                  type="button"
                  onClick={() => setTab("cine4d")}
                  className="underline text-cyan-300 hover:text-cyan-200 transition"
                >
                  4D Cine tab
                </button>
                {" "}and select ED/ES frame indices from one unified volume.
              </span>
            </div>
          )}
          </>
        )}

        {/* 4D CINE MODE */}
        {tab === "cine4d" && (
          <div className="space-y-4">
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => handleFileDrop(e, "cine")}
              className={`relative rounded-xl border-2 border-dashed p-6 text-center transition-all ${
                cineFile
                  ? "border-emerald-500/50 bg-emerald-950/10"
                  : "border-slate-700/80 hover:border-cyan-500/60 bg-slate-900/40"
              }`}
            >
              <input
                ref={cineInputRef}
                type="file"
                accept=".nii,.gz"
                className="hidden"
                onChange={(e) => {
                  if (e.target.files?.[0]) setCineFile(e.target.files[0]);
                }}
              />
              {cineFile ? (
                <div className="flex items-center justify-between gap-3 p-3 bg-slate-900/80 rounded-lg border border-slate-700">
                  <div className="flex items-center gap-3 overflow-hidden text-left">
                    <FileCheck2 className="w-6 h-6 text-emerald-400 flex-shrink-0" />
                    <div className="overflow-hidden">
                      <p className="text-sm font-semibold text-white truncate">
                        {cineFile.name}
                      </p>
                      <p className="text-xs text-slate-400">
                        {formatFileSize(cineFile.size)} • 4D Cine Cardiac MRI
                      </p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setCineFile(null)}
                    className="p-1 hover:bg-slate-800 rounded text-slate-400 hover:text-rose-400 transition"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>
              ) : (
                <div
                  onClick={() => cineInputRef.current?.click()}
                  className="cursor-pointer py-4 flex flex-col items-center justify-center space-y-2"
                >
                  <div className="w-12 h-12 rounded-full bg-cyan-950/60 border border-cyan-800/60 flex items-center justify-center text-cyan-400">
                    <Layers className="w-6 h-6" />
                  </div>
                  <p className="text-sm font-semibold text-slate-200">
                    Upload 4D Cine Cardiac MRI (.nii / .nii.gz)
                  </p>
                  <p className="text-xs text-slate-400">
                    Click to browse or drag and drop a 4D volumetric temporal study
                  </p>
                </div>
              )}
            </div>

            <div className="grid grid-cols-2 gap-4 p-4 rounded-xl bg-slate-900/60 border border-slate-800">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  ED Frame Index (1-based)
                </label>
                <input
                  type="number"
                  min="1"
                  max="60"
                  value={edFrame}
                  onChange={(e) => setEdFrame(Math.max(1, parseInt(e.target.value) || 1))}
                  className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-sm text-white focus:outline-none focus:border-cyan-500"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  ES Frame Index (1-based)
                </label>
                <input
                  type="number"
                  min="1"
                  max="60"
                  value={esFrame}
                  onChange={(e) => setEsFrame(Math.max(1, parseInt(e.target.value) || 1))}
                  className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-sm text-white focus:outline-none focus:border-cyan-500"
                />
              </div>
            </div>
          </div>
        )}

        {/* DEMOGRAPHICS & TTA CONFIGURATION */}
        <div className="pt-2">
          <button
            type="button"
            onClick={() => setShowDemographics(!showDemographics)}
            className="flex items-center justify-between w-full p-3 rounded-xl bg-slate-900/50 hover:bg-slate-900 border border-slate-800 text-xs font-medium text-slate-300 transition"
          >
            <div className="flex items-center gap-2">
              <User className="w-4 h-4 text-cyan-400" />
              <span>Patient Demographics & BSA Indexing</span>
              <span className="text-slate-500 text-[11px]">
                ({heightCm} cm, {weightKg} kg → BSA ~{previewBsa} m²)
              </span>
            </div>
            <Sliders className="w-3.5 h-3.5 text-slate-400" />
          </button>

          {showDemographics && (
            <div className="mt-3 p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-400 mb-1">
                    Height (cm)
                  </label>
                  <input
                    type="number"
                    min="100"
                    max="240"
                    value={heightCm}
                    onChange={(e) => setHeightCm(parseFloat(e.target.value) || 170)}
                    className="w-full px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-700 text-sm text-white focus:outline-none focus:border-cyan-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-400 mb-1">
                    Weight (kg)
                  </label>
                  <input
                    type="number"
                    min="30"
                    max="250"
                    value={weightKg}
                    onChange={(e) => setWeightKg(parseFloat(e.target.value) || 70)}
                    className="w-full px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-700 text-sm text-white focus:outline-none focus:border-cyan-500"
                  />
                </div>
              </div>

              <div className="flex items-center justify-between pt-2 border-t border-slate-800 text-xs">
                <span className="text-slate-400">
                  DuBois Body Surface Area (BSA):
                </span>
                <span className="font-mono font-semibold text-cyan-400">
                  {previewBsa} m²
                </span>
              </div>
            </div>
          )}
        </div>

        {/* TTA & CONFIRMATION CONTROLS */}
        <div className="space-y-3 pt-2">
          <label className="flex items-start gap-2.5 cursor-pointer text-xs text-slate-300 bg-slate-900/60 p-2.5 rounded-xl border border-slate-800">
            <input
              type="checkbox"
              checked={userConfirmed}
              onChange={(e) => setUserConfirmed(e.target.checked)}
              className="w-4 h-4 mt-0.5 rounded border-slate-700 text-cyan-500 focus:ring-cyan-500/20 bg-slate-900 flex-shrink-0"
            />
            <span>
              <strong className="text-white">Clinical Phase Confirmation:</strong> I confirm that the selected volumes or frame indices represent the intended End-Diastole (maximum ventricular filling) and End-Systole (maximum systolic contraction) phases.
            </span>
          </label>

          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-1">
            {/* TTA Toggle */}
            <label className="flex items-center gap-2.5 cursor-pointer text-xs text-slate-400">
              <input
                type="checkbox"
                checked={ttaEnabled}
                onChange={(e) => setTtaEnabled(e.target.checked)}
                className="w-4 h-4 rounded border-slate-700 text-cyan-500 focus:ring-cyan-500/20 bg-slate-900"
              />
              <span>Test-Time Augmentation (4-Way Spatial Flip TTA)</span>
            </label>

            {/* Run Analysis Action Button */}
            <button
              type="submit"
              disabled={isLoading || sampleLoading}
              className="w-full sm:w-auto px-6 py-3 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-semibold text-sm shadow-lg shadow-cyan-600/25 transition-all transform hover:-translate-y-0.5 active:translate-y-0 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
            {isLoading ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                <span>Segmenting & Analyzing...</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-white" />
                <span>Run PULSE Analysis</span>
              </>
            )}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
};
