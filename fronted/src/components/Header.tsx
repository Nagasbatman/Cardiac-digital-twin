"use client";

import React, { useEffect, useState } from "react";
import { Activity, Cpu, Heart, CheckCircle2, AlertCircle, ShieldCheck } from "lucide-react";
import { fetchHealth } from "@/config/api";
import { HealthStatus } from "@/types/cardiac";

export const Header: React.FC = () => {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [isChecking, setIsChecking] = useState(true);

  useEffect(() => {
    let mounted = true;
    const checkServerHealth = async () => {
      try {
        const data = await fetchHealth();
        if (mounted) {
          setHealth(data);
          setIsChecking(false);
        }
      } catch {
        if (mounted) {
          setHealth(null);
          setIsChecking(false);
        }
      }
    };

    checkServerHealth();
    const interval = setInterval(checkServerHealth, 10000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <header className="w-full border-b border-slate-800/80 bg-[#0a1020]/80 backdrop-blur-md sticky top-0 z-40 transition-all">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex flex-col md:flex-row items-center justify-between gap-4">
        {/* Brand identity */}
        <div className="flex items-center gap-3.5">
          <div className="relative flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-600 via-blue-600 to-indigo-600 shadow-lg shadow-cyan-500/20">
            <Heart className="w-5 h-5 text-white animate-heartbeat" />
            <div className="absolute -inset-0.5 rounded-xl bg-cyan-400/20 blur-sm -z-10" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-1.5">
                PULSE <span className="text-cyan-400 font-light">Digital Twin</span>
              </h1>
              <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                4-Fold Ensemble
              </span>
            </div>
            <p className="text-xs text-slate-400 font-normal">
              Cardiac MRI Segmentation, 23 Biomarkers & 5-Class ACDC Diagnosis
            </p>
          </div>
        </div>

        {/* Server & Engine Telemetry */}
        <div className="flex items-center gap-3">
          {/* Hardware & Backend Status Pill */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900/90 border border-slate-800 text-xs">
            {isChecking ? (
              <>
                <div className="w-2 h-2 rounded-full bg-amber-400 animate-ping" />
                <span className="text-slate-400">Connecting to API...</span>
              </>
            ) : health ? (
              <>
                <div className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_8px_#34d399]" />
                <span className="text-slate-300 font-medium">Backend Ready</span>
                <span className="text-slate-600">|</span>
                <div className="flex items-center gap-1 text-cyan-400 font-mono text-[11px]">
                  <Cpu className="w-3.5 h-3.5 text-cyan-400" />
                  <span>{health.device.toUpperCase()}</span>
                </div>
              </>
            ) : (
              <>
                <AlertCircle className="w-3.5 h-3.5 text-rose-400" />
                <span className="text-rose-400 font-medium">API Offline (port 8000)</span>
              </>
            )}
          </div>

          {/* Model Spec Badge */}
          <div className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-950/40 border border-indigo-800/40 text-xs text-indigo-300">
            <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" />
            <span>Folds 0–3 Active</span>
          </div>
        </div>
      </div>
    </header>
  );
};
