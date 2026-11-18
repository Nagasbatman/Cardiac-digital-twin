"use client";

import React, { useEffect, useRef, useState } from "react";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { HeaderStatusArea } from "@/components/cardiovascular-twin/HeaderStatusArea";
import { PatientCohortSelector } from "@/components/cardiovascular-twin/PatientCohortSelector";
import { CurrentCardiovascularState } from "@/components/cardiovascular-twin/CurrentCardiovascularState";
import { RecordedHistoryView } from "@/components/cardiovascular-twin/RecordedHistoryView";
import { WhatIfSimulator } from "@/components/cardiovascular-twin/WhatIfSimulator";
import {
  clearScenarios,
  fetchCardioPresets,
  fetchPatientAnalysis,
  fetchPatientObservations,
  fetchPatientProfile,
  fetchPatientProvenance,
  fetchPatients,
  fetchPatientTrends,
  fetchScenarios,
  runPresetSimulation,
  runWhatIfScenario,
} from "@/config/api";
import {
  CategoryAnalysis,
  ClinicalObservation,
  PatientSummary,
  PresetInfo,
  ProvenanceReport,
  SampleProfile,
  ScenarioComparisonView,
  ScenarioSummary,
  SimulationResponse,
  TrendCategory,
} from "@/types/cardiovascular_twin";

export default function CardiovascularTwinPage() {
  // Session ID for in-memory temporary scenario history
  const sessionIdRef = useRef<string>("");
  if (!sessionIdRef.current && typeof window !== "undefined") {
    sessionIdRef.current = `session_${Math.random().toString(36).substring(2, 11)}_${Date.now()}`;
  }

  // Active patient selection state
  const [selectedPatientId, setSelectedPatientId] = useState<number | null>(10009482);
  const [patientIds, setPatientIds] = useState<number[]>([]);
  const [sampleProfiles, setSampleProfiles] = useState<SampleProfile[]>([]);
  const [totalPatients, setTotalPatients] = useState<number>(1500);

  // Patient data models
  const [summary, setSummary] = useState<PatientSummary | null>(null);
  const [analysis, setAnalysis] = useState<CategoryAnalysis[]>([]);
  const [trends, setTrends] = useState<TrendCategory[]>([]);
  const [observations, setObservations] = useState<ClinicalObservation[]>([]);
  const [totalObservations, setTotalObservations] = useState<number>(0);
  const [provenance, setProvenance] = useState<ProvenanceReport | null>(null);

  // Observation filtering & pagination
  const [obsFilter, setObsFilter] = useState<string>("All");
  const [obsPage, setObsPage] = useState<number>(1);
  const obsPageSize = 15;

  // Simulation & presets state
  const [presets, setPresets] = useState<Record<string, PresetInfo>>({});
  const [selectedPreset, setSelectedPreset] = useState<string>("Healthy Adult");
  const [simulationResult, setSimulationResult] = useState<SimulationResponse | null>(null);
  const [scenarioComparison, setScenarioComparison] = useState<ScenarioComparisonView | null>(null);
  const [sessionScenarios, setSessionScenarios] = useState<ScenarioSummary[]>([]);

  // UI state
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSimLoading, setIsSimLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Load initial cohort and preset list
  useEffect(() => {
    let mounted = true;
    const initializeData = async () => {
      try {
        const [patientsRes, presetsRes] = await Promise.all([
          fetchPatients(undefined, 100),
          fetchCardioPresets(),
        ]);
        if (mounted) {
          setPatientIds(patientsRes.patient_ids);
          setSampleProfiles(patientsRes.sample_profiles);
          setTotalPatients(patientsRes.total_patients);
          setPresets(presetsRes.presets);
          if (presetsRes.presets["Healthy Adult"]) {
            setSelectedPreset("Healthy Adult");
          } else {
            const firstKey = Object.keys(presetsRes.presets)[0];
            if (firstKey) setSelectedPreset(firstKey);
          }
        }
      } catch (err: any) {
        if (mounted) {
          console.error("Initialization error:", err);
          setErrorMessage(err.message || "Failed to initialize Cardiovascular Digital Twin.");
        }
      }
    };

    initializeData();
    return () => {
      mounted = false;
    };
  }, []);

  // Load patient clinical data when selectedPatientId changes
  useEffect(() => {
    if (!selectedPatientId) return;

    let mounted = true;
    const loadPatientData = async () => {
      setIsLoading(true);
      setErrorMessage(null);
      try {
        const [profileRes, analysisRes, trendsRes, provRes] = await Promise.all([
          fetchPatientProfile(selectedPatientId),
          fetchPatientAnalysis(selectedPatientId),
          fetchPatientTrends(selectedPatientId),
          fetchPatientProvenance(selectedPatientId),
        ]);

        if (mounted) {
          setSummary(profileRes.summary);
          setAnalysis(analysisRes.analysis);
          setTrends(trendsRes.trends);
          setProvenance(provRes.provenance);
        }
      } catch (err: any) {
        if (mounted) {
          console.error("Error loading patient data:", err);
          setErrorMessage(err.message || `Failed to load data for patient ${selectedPatientId}`);
        }
      } finally {
        if (mounted) setIsLoading(false);
      }
    };

    loadPatientData();
    return () => {
      mounted = false;
    };
  }, [selectedPatientId]);

  // Load observations when filter or page changes
  useEffect(() => {
    if (!selectedPatientId) return;

    let mounted = true;
    const loadObs = async () => {
      try {
        const measName = obsFilter === "All" ? undefined : obsFilter;
        const offset = (obsPage - 1) * obsPageSize;
        const res = await fetchPatientObservations(
          selectedPatientId,
          undefined,
          measName,
          obsPageSize,
          offset
        );
        if (mounted) {
          setObservations(res.observations);
          setTotalObservations(res.total);
        }
      } catch (err: any) {
        console.error("Error loading observations:", err);
      }
    };

    loadObs();
    return () => {
      mounted = false;
    };
  }, [selectedPatientId, obsFilter, obsPage]);

  // Handlers
  const handleSelectPatient = (subjectId: number) => {
    setSelectedPatientId(subjectId);
    setObsPage(1);
    setObsFilter("All");
    setSimulationResult(null);
    setScenarioComparison(null);
  };

  const handleRefresh = async () => {
    if (!selectedPatientId) return;
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const [profileRes, analysisRes, trendsRes, provRes] = await Promise.all([
        fetchPatientProfile(selectedPatientId),
        fetchPatientAnalysis(selectedPatientId),
        fetchPatientTrends(selectedPatientId),
        fetchPatientProvenance(selectedPatientId),
      ]);
      setSummary(profileRes.summary);
      setAnalysis(analysisRes.analysis);
      setTrends(trendsRes.trends);
      setProvenance(provRes.provenance);
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to refresh patient data.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleRunPreset = async (presetName: string, duration: number) => {
    if (!selectedPatientId) return;
    setIsSimLoading(true);
    setErrorMessage(null);
    try {
      const res = await runPresetSimulation(
        {
          subject_id: selectedPatientId,
          preset_name: presetName,
          duration,
          session_id: sessionIdRef.current,
        },
        sessionIdRef.current
      );
      setSimulationResult(res);

      // Refresh session scenario history
      const hist = await fetchScenarios(sessionIdRef.current);
      setSessionScenarios(hist.scenarios);
      setScenarioComparison(hist.comparison);
    } catch (err: any) {
      setErrorMessage(err.message || "CardioSim preset simulation failed.");
    } finally {
      setIsSimLoading(false);
    }
  };

  const handleRunWhatIf = async (params: {
    scenario_name: string;
    preset_name: string;
    hr: number;
    contract: number;
    resist: number;
    compl: number;
    duration: number;
  }) => {
    setIsSimLoading(true);
    setErrorMessage(null);
    try {
      const res = await runWhatIfScenario(
        {
          subject_id: selectedPatientId || undefined,
          scenario_name: params.scenario_name,
          preset_name: params.preset_name,
          hr: params.hr,
          contract: params.contract,
          resist: params.resist,
          compl: params.compl,
          duration: params.duration,
          session_id: sessionIdRef.current,
        },
        sessionIdRef.current
      );

      setScenarioComparison(res.comparison);

      // Refresh scenario history
      const hist = await fetchScenarios(sessionIdRef.current);
      setSessionScenarios(hist.scenarios);
    } catch (err: any) {
      setErrorMessage(err.message || "Custom what-if scenario execution failed.");
    } finally {
      setIsSimLoading(false);
    }
  };

  const handleClearHistory = async () => {
    setIsSimLoading(true);
    try {
      await clearScenarios(sessionIdRef.current);
      setSessionScenarios([]);
      setScenarioComparison(null);
      setSimulationResult(null);
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to clear scenario history.");
    } finally {
      setIsSimLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#070b14] text-slate-100 flex flex-col font-sans">
      <Header />

      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 md:py-10 w-full space-y-10">
        {/* AREA 1: Header & Data Status Telemetry */}
        <HeaderStatusArea
          summary={summary}
          selectedId={selectedPatientId}
          isLoading={isLoading}
          onRefresh={handleRefresh}
        />

        {/* AREA 2: Example Patients & Profile Selector */}
        <PatientCohortSelector
          selectedId={selectedPatientId}
          summary={summary}
          patientIds={patientIds}
          sampleProfiles={sampleProfiles}
          totalPatients={totalPatients}
          onSelectPatient={handleSelectPatient}
          isLoading={isLoading}
        />

        {/* AREA 3: 01 · Current Cardiovascular State */}
        <CurrentCardiovascularState analysis={analysis} isLoading={isLoading} />

        {/* AREA 4: 02 · Recorded Cardiovascular History */}
        <RecordedHistoryView
          trends={trends}
          observations={observations}
          totalObservations={totalObservations}
          isLoading={isLoading}
          currentPage={obsPage}
          pageSize={obsPageSize}
          onPageChange={setObsPage}
          selectedFilter={obsFilter}
          onFilterChange={(f) => {
            setObsFilter(f);
            setObsPage(1);
          }}
        />

        {/* AREA 5: 03 · What-if Scenario Simulator */}
        <WhatIfSimulator
          provenance={provenance}
          presets={presets}
          selectedPreset={selectedPreset}
          onSelectPreset={setSelectedPreset}
          onRunPreset={handleRunPreset}
          onRunWhatIf={handleRunWhatIf}
          simulationResult={simulationResult}
          scenarioComparison={scenarioComparison}
          sessionScenarios={sessionScenarios}
          onClearHistory={handleClearHistory}
          isLoading={isSimLoading}
          errorMessage={errorMessage}
        />
      </main>

      <Footer />
    </div>
  );
}

