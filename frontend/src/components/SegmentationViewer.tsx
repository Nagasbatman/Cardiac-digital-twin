"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Layers,
  ChevronLeft,
  ChevronRight,
  Eye,
  Sliders,
  Maximize2,
  Minimize2,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Sparkles,
  Columns,
  Square,
  Sun,
  Contrast,
  Move
} from "lucide-react";
import { SliceData, AnalysisMetadata } from "@/types/cardiac";

interface SegmentationViewerProps {
  slices: SliceData[];
  metadata: AnalysisMetadata;
}

export const SegmentationViewer: React.FC<SegmentationViewerProps> = ({
  slices,
  metadata,
}) => {
  const [currentSliceIdx, setCurrentSliceIdx] = useState<number>(
    metadata.mid_slice - 1 || 0
  );
  const [viewMode, setViewMode] = useState<"overlay" | "raw" | "comparison">("overlay");
  const [layoutMode, setLayoutMode] = useState<"dual" | "ed_only" | "es_only">("dual");
  
  // Doctor diagnostic view controls: Zoom, Pan, Brightness, Contrast
  const [zoom, setZoom] = useState<number>(1.4); // Default to 1.4x for immediate clearer view of cardiac structures
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [dragStart, setDragStart] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [brightness, setBrightness] = useState<number>(100);
  const [contrast, setContrast] = useState<number>(105);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);

  useEffect(() => {
    if (metadata.mid_slice) {
      setCurrentSliceIdx(Math.max(0, Math.min(metadata.mid_slice - 1, slices.length - 1)));
    }
  }, [metadata, slices]);

  const totalSlices = slices.length;
  const activeSlice = slices[currentSliceIdx] || slices[0];

  const handlePrev = () => {
    setCurrentSliceIdx((prev) => Math.max(0, prev - 1));
  };

  const handleNext = () => {
    setCurrentSliceIdx((prev) => Math.min(totalSlices - 1, prev + 1));
  };

  const resetView = () => {
    setZoom(1.4);
    setPan({ x: 0, y: 0 });
    setBrightness(100);
    setContrast(105);
  };

  // Mouse pan handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    if (zoom > 1) {
      setIsDragging(true);
      setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging) {
      setPan({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      });
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const getSliceLevel = (idx: number, total: number) => {
    const fraction = (idx + 1) / total;
    if (fraction <= 0.35) return "Basal Level (Base)";
    if (fraction <= 0.70) return "Mid-Ventricular Level";
    return "Apical Level (Apex)";
  };

  if (!slices || slices.length === 0) {
    return (
      <div className="glass-panel p-8 text-center text-slate-400">
        <Layers className="w-10 h-10 mx-auto text-slate-600 mb-2" />
        <p>No segmentation slices available.</p>
      </div>
    );
  }

  const imageFilterStyle = {
    filter: `brightness(${brightness}%) contrast(${contrast}%)`,
    transform: `scale(${zoom}) translate(${pan.x / zoom}px, ${pan.y / zoom}px)`,
    transition: isDragging ? "none" : "transform 0.15s ease-out",
  };

  return (
    <div
      className={`glass-panel p-5 sm:p-6 space-y-5 transition-all ${
        isFullscreen
          ? "fixed inset-0 z-50 overflow-y-auto bg-[#070b14]/98 rounded-none p-6 sm:p-8"
          : ""
      }`}
    >
      {/* Top Header & View Controls */}
      <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 pb-3 border-b border-slate-800">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-cyan-950/60 border border-cyan-800/40 text-cyan-400">
            <Layers className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold text-white">
                Volumetric Cardiac Segmentation Overlays
              </h3>
              <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                PACS Diagnostic Mode
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Short-Axis MRI • Resolution {metadata.dimensions[0]}×{metadata.dimensions[1]} • Spacing {metadata.voxel_spacing[0]}×{metadata.voxel_spacing[1]}×{metadata.voxel_spacing[2]} mm
            </p>
          </div>
        </div>

        {/* Toolbar: Layout Mode, View Mode, Zoom & Fullscreen */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Layout Selector: Dual vs Focused ED vs Focused ES */}
          <div className="flex items-center gap-1 p-1 bg-slate-900/90 rounded-lg border border-slate-800 text-xs">
            <button
              type="button"
              onClick={() => setLayoutMode("dual")}
              className={`px-2.5 py-1.5 rounded-md font-medium transition flex items-center gap-1 ${
                layoutMode === "dual"
                  ? "bg-cyan-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-white"
              }`}
              title="Dual View (Side-by-Side)"
            >
              <Columns className="w-3.5 h-3.5" />
              <span>Dual</span>
            </button>
            <button
              type="button"
              onClick={() => setLayoutMode("ed_only")}
              className={`px-2.5 py-1.5 rounded-md font-medium transition flex items-center gap-1 ${
                layoutMode === "ed_only"
                  ? "bg-cyan-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-white"
              }`}
              title="Enlarge End-Diastole Only"
            >
              <Square className="w-3.5 h-3.5" />
              <span>Focus ED</span>
            </button>
            <button
              type="button"
              onClick={() => setLayoutMode("es_only")}
              className={`px-2.5 py-1.5 rounded-md font-medium transition flex items-center gap-1 ${
                layoutMode === "es_only"
                  ? "bg-cyan-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-white"
              }`}
              title="Enlarge End-Systole Only"
            >
              <Square className="w-3.5 h-3.5" />
              <span>Focus ES</span>
            </button>
          </div>

          {/* View Mode: Overlay vs Raw vs Compare */}
          <div className="flex items-center gap-1 p-1 bg-slate-900/90 rounded-lg border border-slate-800 text-xs">
            <button
              type="button"
              onClick={() => setViewMode("overlay")}
              className={`px-2.5 py-1.5 rounded-md font-medium transition ${
                viewMode === "overlay"
                  ? "bg-blue-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              Overlay
            </button>
            <button
              type="button"
              onClick={() => setViewMode("raw")}
              className={`px-2.5 py-1.5 rounded-md font-medium transition ${
                viewMode === "raw"
                  ? "bg-blue-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              Raw MRI
            </button>
            <button
              type="button"
              onClick={() => setViewMode("comparison")}
              className={`px-2.5 py-1.5 rounded-md font-medium transition ${
                viewMode === "comparison"
                  ? "bg-blue-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              Compare
            </button>
          </div>

          {/* Zoom Buttons */}
          <div className="flex items-center gap-1 p-1 bg-slate-900/90 rounded-lg border border-slate-800 text-xs">
            <button
              type="button"
              onClick={() => setZoom((z) => Math.max(1, parseFloat((z - 0.2).toFixed(1))))}
              className="p-1.5 rounded hover:bg-slate-800 text-slate-300 hover:text-white transition"
              title="Zoom Out"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <span className="font-mono text-cyan-400 px-1.5 font-semibold text-[11px] min-w-[38px] text-center">
              {Math.round(zoom * 100)}%
            </span>
            <button
              type="button"
              onClick={() => setZoom((z) => Math.min(3, parseFloat((z + 0.2).toFixed(1))))}
              className="p-1.5 rounded hover:bg-slate-800 text-slate-300 hover:text-white transition"
              title="Zoom In"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={resetView}
              className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-cyan-400 transition"
              title="Reset Zoom & Pan"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Fullscreen Expand Button */}
          <button
            type="button"
            onClick={() => setIsFullscreen(!isFullscreen)}
            className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 hover:text-white hover:border-slate-700 transition"
            title={isFullscreen ? "Exit Fullscreen" : "Diagnostic Fullscreen View"}
          >
            {isFullscreen ? (
              <Minimize2 className="w-4 h-4 text-cyan-400" />
            ) : (
              <Maximize2 className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>

      {/* Anatomical Color Legend & PACS Controls Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-2.5 rounded-xl bg-slate-900/70 border border-slate-800/80 text-xs">
        <div className="flex items-center gap-4 flex-wrap">
          <span className="text-slate-400 font-medium">Anatomical Legend:</span>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-[#dc2828] shadow-[0_0_8px_#dc2828]" />
            <span className="text-slate-200 font-semibold">Right Ventricle (RV)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-[#28c83c] shadow-[0_0_8px_#28c83c]" />
            <span className="text-slate-200 font-semibold">Myocardium (Myo)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-[#325ae6] shadow-[0_0_8px_#325ae6]" />
            <span className="text-slate-200 font-semibold">Left Ventricle (LV)</span>
          </div>
        </div>

        {/* Quick Zoom Presets for Clinicians */}
        <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
          <span className="hidden sm:inline">Magnification:</span>
          {[1.0, 1.4, 1.8, 2.2].map((preset) => (
            <button
              key={preset}
              type="button"
              onClick={() => {
                setZoom(preset);
                setPan({ x: 0, y: 0 });
              }}
              className={`px-2 py-0.5 rounded-md font-mono transition ${
                zoom === preset
                  ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40"
                  : "bg-slate-800/80 text-slate-400 hover:text-white"
              }`}
            >
              {preset}x
            </button>
          ))}
          {zoom > 1 && (
            <span className="text-[10px] text-cyan-400/80 flex items-center gap-1 ml-1">
              <Move className="w-3 h-3" /> Click & drag to pan
            </span>
          )}
        </div>
      </div>

      {/* Slices Display Grid - Enforced Large Dimensions */}
      <div
        className={`grid gap-6 ${
          layoutMode === "dual" ? "grid-cols-1 md:grid-cols-2" : "grid-cols-1 max-w-4xl mx-auto"
        }`}
      >
        {/* End-Diastole (ED) View */}
        {(layoutMode === "dual" || layoutMode === "ed_only") && (
          <div className="flex flex-col rounded-2xl bg-slate-950 border border-slate-800/90 overflow-hidden shadow-2xl">
            <div className="flex items-center justify-between px-4 py-3 bg-slate-900/90 border-b border-slate-800 text-xs">
              <span className="font-bold text-cyan-400 flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 shadow-[0_0_8px_#22d3ee]" />
                End-Diastole (ED) • Maximum Diastolic Filling
              </span>
              <span className="text-[11px] text-slate-400 font-mono">
                Frame: 1 • Voxel: {metadata.dimensions[0]}×{metadata.dimensions[1]}
              </span>
            </div>

            {/* Large Viewport (minimum 540px high) */}
            <div
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onMouseLeave={handleMouseUp}
              className={`relative w-full h-[520px] sm:h-[600px] lg:h-[640px] bg-[#02050b] flex items-center justify-center overflow-hidden select-none ${
                zoom > 1 ? (isDragging ? "cursor-grabbing" : "cursor-grab") : "cursor-default"
              }`}
            >
              {viewMode === "overlay" && (
                <img
                  src={activeSlice.ed_overlay}
                  alt={`ED Slice ${activeSlice.slice_index}`}
                  style={imageFilterStyle}
                  className="max-h-full max-w-full object-contain rounded-lg pointer-events-none"
                />
              )}
              {viewMode === "raw" && (
                <img
                  src={activeSlice.ed_raw}
                  alt={`ED Raw Slice ${activeSlice.slice_index}`}
                  style={imageFilterStyle}
                  className="max-h-full max-w-full object-contain rounded-lg pointer-events-none"
                />
              )}
              {viewMode === "comparison" && (
                <div className="grid grid-cols-2 gap-4 h-full w-full p-4">
                  <div className="relative flex flex-col items-center justify-center bg-black/50 rounded-xl overflow-hidden border border-slate-800/60">
                    <span className="absolute top-2 left-2 z-10 text-[10px] font-mono bg-slate-900/90 px-2 py-0.5 rounded text-slate-300 border border-slate-700">
                      Raw Cine
                    </span>
                    <img
                      src={activeSlice.ed_raw}
                      alt="ED Raw"
                      style={imageFilterStyle}
                      className="max-h-full max-w-full object-contain"
                    />
                  </div>
                  <div className="relative flex flex-col items-center justify-center bg-black/50 rounded-xl overflow-hidden border border-slate-800/60">
                    <span className="absolute top-2 left-2 z-10 text-[10px] font-mono bg-cyan-950/90 px-2 py-0.5 rounded text-cyan-300 border border-cyan-800">
                      PULSE Segmentation
                    </span>
                    <img
                      src={activeSlice.ed_overlay}
                      alt="ED Overlay"
                      style={imageFilterStyle}
                      className="max-h-full max-w-full object-contain"
                    />
                  </div>
                </div>
              )}

              {/* In-Viewer Floating Info Tag */}
              <div className="absolute bottom-3 left-3 bg-slate-900/80 backdrop-blur-md px-2.5 py-1 rounded-md border border-slate-800 text-[11px] font-mono text-slate-300 pointer-events-none flex items-center gap-2">
                <span>ED Slice {activeSlice.slice_index}</span>
                <span className="text-slate-600">|</span>
                <span className="text-cyan-400">{Math.round(zoom * 100)}% Mag</span>
              </div>
            </div>
          </div>
        )}

        {/* End-Systole (ES) View */}
        {(layoutMode === "dual" || layoutMode === "es_only") && (
          <div className="flex flex-col rounded-2xl bg-slate-950 border border-slate-800/90 overflow-hidden shadow-2xl">
            <div className="flex items-center justify-between px-4 py-3 bg-slate-900/90 border-b border-slate-800 text-xs">
              <span className="font-bold text-blue-400 flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-blue-400 shadow-[0_0_8px_#60a5fa]" />
                End-Systole (ES) • Maximum Systolic Contraction
              </span>
              <span className="text-[11px] text-slate-400 font-mono">
                Frame: 14 • Voxel: {metadata.dimensions[0]}×{metadata.dimensions[1]}
              </span>
            </div>

            {/* Large Viewport (minimum 540px high) */}
            <div
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onMouseLeave={handleMouseUp}
              className={`relative w-full h-[520px] sm:h-[600px] lg:h-[640px] bg-[#02050b] flex items-center justify-center overflow-hidden select-none ${
                zoom > 1 ? (isDragging ? "cursor-grabbing" : "cursor-grab") : "cursor-default"
              }`}
            >
              {viewMode === "overlay" && (
                <img
                  src={activeSlice.es_overlay}
                  alt={`ES Slice ${activeSlice.slice_index}`}
                  style={imageFilterStyle}
                  className="max-h-full max-w-full object-contain rounded-lg pointer-events-none"
                />
              )}
              {viewMode === "raw" && (
                <img
                  src={activeSlice.es_raw}
                  alt={`ES Raw Slice ${activeSlice.slice_index}`}
                  style={imageFilterStyle}
                  className="max-h-full max-w-full object-contain rounded-lg pointer-events-none"
                />
              )}
              {viewMode === "comparison" && (
                <div className="grid grid-cols-2 gap-4 h-full w-full p-4">
                  <div className="relative flex flex-col items-center justify-center bg-black/50 rounded-xl overflow-hidden border border-slate-800/60">
                    <span className="absolute top-2 left-2 z-10 text-[10px] font-mono bg-slate-900/90 px-2 py-0.5 rounded text-slate-300 border border-slate-700">
                      Raw Cine
                    </span>
                    <img
                      src={activeSlice.es_raw}
                      alt="ES Raw"
                      style={imageFilterStyle}
                      className="max-h-full max-w-full object-contain"
                    />
                  </div>
                  <div className="relative flex flex-col items-center justify-center bg-black/50 rounded-xl overflow-hidden border border-slate-800/60">
                    <span className="absolute top-2 left-2 z-10 text-[10px] font-mono bg-blue-950/90 px-2 py-0.5 rounded text-blue-300 border border-blue-800">
                      PULSE Segmentation
                    </span>
                    <img
                      src={activeSlice.es_overlay}
                      alt="ES Overlay"
                      style={imageFilterStyle}
                      className="max-h-full max-w-full object-contain"
                    />
                  </div>
                </div>
              )}

              {/* In-Viewer Floating Info Tag */}
              <div className="absolute bottom-3 left-3 bg-slate-900/80 backdrop-blur-md px-2.5 py-1 rounded-md border border-slate-800 text-[11px] font-mono text-slate-300 pointer-events-none flex items-center gap-2">
                <span>ES Slice {activeSlice.slice_index}</span>
                <span className="text-slate-600">|</span>
                <span className="text-blue-400">{Math.round(zoom * 100)}% Mag</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Interactive Slice Slider & Stepper Bar */}
      <div className="p-4 sm:p-5 rounded-2xl bg-slate-900/90 border border-slate-800 space-y-3.5 shadow-lg">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <Sliders className="w-4 h-4 text-cyan-400" />
            <span className="text-xs sm:text-sm font-bold text-white">
              Short-Axis Anatomical Slice Navigator
            </span>
            <span className="text-xs font-mono font-bold px-2.5 py-0.5 rounded-md bg-cyan-950 border border-cyan-800 text-cyan-300 shadow-sm">
              Slice {currentSliceIdx + 1} of {totalSlices}
            </span>
          </div>
          <span className="text-xs font-semibold text-cyan-300/90 bg-slate-800/80 px-2.5 py-1 rounded-lg border border-slate-700/60">
            {getSliceLevel(currentSliceIdx, totalSlices)}
          </span>
        </div>

        {/* Range Slider */}
        <div className="relative py-1">
          <input
            type="range"
            min={0}
            max={totalSlices - 1}
            value={currentSliceIdx}
            onChange={(e) => setCurrentSliceIdx(parseInt(e.target.value))}
            className="w-full h-2 cursor-pointer"
          />
          <div className="flex justify-between text-[11px] text-slate-400 font-mono pt-1.5 font-medium">
            <span className="flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" /> Base (Slice 1)
            </span>
            <span className="flex items-center gap-1 text-slate-300">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-400" /> Mid-Ventricular
            </span>
            <span className="flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-indigo-400" /> Apex (Slice {totalSlices})
            </span>
          </div>
        </div>

        {/* Stepper Buttons & Controls */}
        <div className="flex items-center justify-between pt-1">
          <button
            type="button"
            onClick={handlePrev}
            disabled={currentSliceIdx === 0}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-xs font-semibold text-slate-200 transition shadow-sm"
          >
            <ChevronLeft className="w-4 h-4" />
            <span>Previous Slice</span>
          </button>

          <span className="text-[11px] text-slate-400 hidden sm:inline">
            Tip: Scrub with the slider or click magnification buttons (1.4x, 1.8x, 2.2x) to inspect wall contours
          </span>

          <button
            type="button"
            onClick={handleNext}
            disabled={currentSliceIdx === totalSlices - 1}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-xs font-semibold text-slate-200 transition shadow-sm"
          >
            <span>Next Slice</span>
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
