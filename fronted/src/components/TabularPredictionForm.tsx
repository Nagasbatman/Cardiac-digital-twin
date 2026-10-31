"use client";

import React from "react";
import {
  HeartTabularInput,
  Gender,
  Ethnicity,
  SmokingStatus,
  YesNo,
  ChestPainType,
} from "@/types/heart_tabular";
import {
  Sparkles,
  RotateCcw,
  Activity,
  User,
  Gauge,
  FlaskConical,
  FileHeart,
  AlertTriangle,
  Stethoscope,
} from "lucide-react";

interface TabularPredictionFormProps {
  formData: Partial<HeartTabularInput>;
  onChange: (field: keyof HeartTabularInput, value: any) => void;
  onSubmit: (e: React.FormEvent) => void;
  onReset: () => void;
  onLoadSample: () => void;
  isLoading: boolean;
  sampleLoading: boolean;
}

export const TabularPredictionForm: React.FC<TabularPredictionFormProps> = ({
  formData,
  onChange,
  onSubmit,
  onReset,
  onLoadSample,
  isLoading,
  sampleLoading,
}) => {
  const handleNumChange = (field: keyof HeartTabularInput, value: string) => {
    if (value === "") {
      onChange(field, undefined);
    } else {
      const num = parseFloat(value);
      onChange(field, isNaN(num) ? undefined : num);
    }
  };

  return (
    <form onSubmit={onSubmit} className="space-y-8">
      {/* Action Bar: Load Sample & Reset */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-4 rounded-xl bg-slate-900/80 border border-slate-800">
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <Stethoscope className="w-4 h-4 text-cyan-400" />
          <span>31 Clinical Parameters expected by CDC NHANES model</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onLoadSample}
            disabled={sampleLoading || isLoading}
            className="flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium bg-cyan-500/10 text-cyan-300 hover:bg-cyan-500/20 border border-cyan-500/30 transition-all disabled:opacity-50"
          >
            <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
            <span>{sampleLoading ? "Loading Sample..." : "Load Sample Patient (High Risk)"}</span>
          </button>
          <button
            type="button"
            onClick={onReset}
            disabled={isLoading}
            className="flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium bg-slate-800 text-slate-300 hover:bg-slate-700 border border-slate-700 transition-all disabled:opacity-50"
          >
            <RotateCcw className="w-3.5 h-3.5 text-slate-400" />
            <span>Reset</span>
          </button>
        </div>
      </div>

      {/* Section 1: Demographics & Socioeconomic */}
      <div className="p-6 rounded-2xl bg-slate-900/50 border border-slate-800/80 space-y-4">
        <div className="flex items-center gap-2.5 pb-3 border-b border-slate-800">
          <User className="w-5 h-5 text-cyan-400" />
          <div>
            <h3 className="text-sm font-semibold text-white">1. Demographics & Socioeconomic Status</h3>
            <p className="text-xs text-slate-400">Age, gender, ethnicity, and education level</p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Age <span className="text-slate-500">(years)</span>
            </label>
            <input
              type="number"
              step="1"
              min="18"
              max="120"
              required
              value={formData.age ?? ""}
              onChange={(e) => handleNumChange("age", e.target.value)}
              placeholder="e.g. 67"
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-white text-sm focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Gender</label>
            <select
              required
              value={formData.gender ?? ""}
              onChange={(e) => onChange("gender", e.target.value as Gender)}
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-white text-sm focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
            >
              <option value="" disabled>Select Gender</option>
              <option value="Male">Male</option>
              <option value="Female">Female</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Ethnicity</label>
            <select
              required
              value={formData.ethnicity ?? ""}
              onChange={(e) => onChange("ethnicity", e.target.value as Ethnicity)}
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-white text-sm focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
            >
              <option value="" disabled>Select Ethnicity</option>
              <option value="Non-Hispanic White">Non-Hispanic White</option>
              <option value="Non-Hispanic Black">Non-Hispanic Black</option>
              <option value="Non-Hispanic Asian">Non-Hispanic Asian</option>
              <option value="Mexican American">Mexican American</option>
              <option value="Other Hispanic">Other Hispanic</option>
              <option value="Other/Multi-Racial">Other / Multi-Racial</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Education Level</label>
            <select
              required
              value={formData.education_level ?? ""}
              onChange={(e) => handleNumChange("education_level", e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-white text-sm focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
            >
              <option value="" disabled>Select Education Level</option>
              <option value="1">1: Less than 9th grade</option>
              <option value="2">2: 9th–11th grade</option>
              <option value="3">3: High school graduate / GED</option>
              <option value="4">4: Some college or AA degree</option>
              <option value="5">5: College graduate or above</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Poverty-Income Ratio <span className="text-slate-500">(0.0 – 5.0)</span>
            </label>
            <input
              type="number"
              step="0.1"
              min="0"
              max="5.0"
              required
              value={formData.poverty_income_ratio ?? ""}
              onChange={(e) => handleNumChange("poverty_income_ratio", e.target.value)}
              placeholder="e.g. 1.3 (ratio to poverty guideline)"
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-white text-sm focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
            />
          </div>
        </div>
      </div>

      {/* Section 2: Anthropometrics & Vital Signs */}
      <div className="p-6 rounded-2xl bg-slate-900/50 border border-slate-800/80 space-y-4">
        <div className="flex items-center gap-2.5 pb-3 border-b border-slate-800">
          <Gauge className="w-5 h-5 text-blue-400" />
          <div>
            <h3 className="text-sm font-semibold text-white">2. Anthropometrics & Vital Signs</h3>
            <p className="text-xs text-slate-400">Body measurements, blood pressure, and resting heart rate</p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Body Mass Index (BMI) <span className="text-slate-500">(kg/m²)</span>
            </label>
            <input
              type="number"
              step="0.1"
              min="10"
              max="80"
              required
              value={formData.bmi ?? ""}
              onChange={(e) => handleNumChange("bmi", e.target.value)}
              placeholder="e.g. 31.5"
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-white text-sm focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Waist Circumference <span className="text-slate-500">(cm)</span>
            </label>
            <input
              type="number"
              step="0.5"
              min="40"
              max="200"
              required
              value={formData.waist_cm ?? ""}
              onChange={(e) => handleNumChange("waist_cm", e.target.value)}
              placeholder="e.g. 112.0"
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-white text-sm focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Height <span className="text-slate-500">(cm)</span>
            </label>
            <input
              type="number"
              step="0.5"
              min="100"
              max="250"
              required
              value={formData.height_cm ?? ""}
              onChange={(e) => handleNumChange("height_cm", e.target.value)}
              placeholder="e.g. 175.0"
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-white text-sm focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Systolic Blood Pressure <span className="text-slate-500">(mmHg)</span>
            </label>
            <input
              type="number"
              step="1"
              min="60"
              max="260"
              required
              value={formData.systolic_bp ?? ""}
              onChange={(e) => handleNumChange("systolic_bp", e.target.value)}
              placeholder="e.g. 158"
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-white text-sm focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Diastolic Blood Pressure <span className="text-slate-500">(mmHg)</span>
            </label>
            <input
              type="number"
              step="1"
              min="30"
              max="150"
              required
              value={formData.diastolic_bp ?? ""}
              onChange={(e) => handleNumChange("diastolic_bp", e.target.value)}
              placeholder="e.g. 84"
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-white text-sm focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Resting Heart Rate <span className="text-slate-500">(bpm)</span>
            </label>
            <input
              type="number"
              step="1"
              min="30"
              max="200"
              required
              value={formData.resting_heart_rate ?? ""}
              onChange={(e) => handleNumChange("resting_heart_rate", e.target.value)}
              placeholder="e.g. 82"
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-white text-sm focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
            />
          </div>
        </div>
      </div>

      {/* Section 3: Laboratory Biomarkers */}
      <div className="p-6 rounded-2xl bg-slate-900/50 border border-slate-800/80 space-y-4">
        <div className="flex items-center gap-2.5 pb-3 border-b border-slate-800">
          <FlaskConical className="w-5 h-5 text-indigo-400" />
          <div>
            <h3 className="text-sm font-semibold text-white">3. Blood & Urine Laboratory Biomarkers</h3>
            <p className="text-xs text-slate-400">Lipid panel, glycemic control, renal markers, and complete blood count</p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Total Cholesterol <span className="text-slate-500">(mg/dL)</span>
            </label>
            <input
              type="number"
              step="1"
              min="50"
              max="500"
              required
              value={formData.total_cholesterol ?? ""}
              onChange={(e) => handleNumChange("total_cholesterol", e.target.value)}
              placeholder="e.g. 240"
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-white text-sm focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              HDL Cholesterol <span className="text-slate-500">(mg/dL)</span>
            </label>
            <input
              type="number"
              step="1"
              min="10"
              max="150"
              required
              value={formData.hdl_cholesterol ?? ""}
              onChange={(e) => handleNumChange("hdl_cholesterol", e.target.value)}
              placeholder="e.g. 34"
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-white text-sm focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              HbA1c <span className="text-slate-500">(%)</span>
            </label>
            <input
              type="number"
              step="0.1"
              min="3.0"
              max="18.0"
              required
              value={formData.hba1c ?? ""}
              onChange={(e) => handleNumChange("hba1c", e.target.value)}
              placeholder="e.g. 7.9"
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-white text-sm focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Serum Creatinine <span className="text-slate-500">(mg/dL)</span>
            </label>
            <input
              type="number"
              step="0.05"
              min="0.1"
              max="15.0"
              required
              value={formData.serum_creatinine ?? ""}
              onChange={(e) => handleNumChange("serum_creatinine", e.target.value)}
              placeholder="e.g. 1.4"
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-white text-sm focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Uric Acid <span className="text-slate-500">(mg/dL)</span>
            </label>
            <input
              type="number"
              step="0.1"
              min="1.0"
              max="20.0"
              required
              value={formData.uric_acid ?? ""}
              onChange={(e) => handleNumChange("uric_acid", e.target.value)}
              placeholder="e.g. 7.6"
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-white text-sm focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Albumin-Creatinine Ratio (ACR) <span className="text-slate-500">(mg/g)</span>
            </label>
            <input
              type="number"
              step="1"
              min="0.1"
              max="10000"
              required
              value={formData.albumin_creatinine_ratio ?? ""}
              onChange={(e) => handleNumChange("albumin_creatinine_ratio", e.target.value)}
              placeholder="e.g. 85.0"
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-white text-sm focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              White Blood Cells <span className="text-slate-500">(1000 cells/µL)</span>
            </label>
            <input
              type="number"
              step="0.1"
              min="1.0"
              max="50.0"
              required
              value={formData.white_blood_cells ?? ""}
              onChange={(e) => handleNumChange("white_blood_cells", e.target.value)}
              placeholder="e.g. 8.9"
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-white text-sm focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Hemoglobin <span className="text-slate-500">(g/dL)</span>
            </label>
            <input
              type="number"
              step="0.1"
              min="4.0"
              max="25.0"
              required
              value={formData.hemoglobin ?? ""}
              onChange={(e) => handleNumChange("hemoglobin", e.target.value)}
              placeholder="e.g. 13.4"
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-white text-sm focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Red Cell Distribution Width (RDW) <span className="text-slate-500">(%)</span>
            </label>
            <input
              type="number"
              step="0.1"
              min="8.0"
              max="35.0"
              required
              value={formData.rdw ?? ""}
              onChange={(e) => handleNumChange("rdw", e.target.value)}
              placeholder="e.g. 14.8"
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-white text-sm focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
            />
          </div>
        </div>
      </div>

      {/* Section 4: Medical History & Lifestyle */}
      <div className="p-6 rounded-2xl bg-slate-900/50 border border-slate-800/80 space-y-4">
        <div className="flex items-center gap-2.5 pb-3 border-b border-slate-800">
          <FileHeart className="w-5 h-5 text-rose-400" />
          <div>
            <h3 className="text-sm font-semibold text-white">4. Medical History & Lifestyle Factors</h3>
            <p className="text-xs text-slate-400">Cardiovascular comorbidities and risk profile</p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Smoking Status</label>
            <select
              required
              value={formData.smoking_status ?? ""}
              onChange={(e) => onChange("smoking_status", e.target.value as SmokingStatus)}
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-white text-sm focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
            >
              <option value="" disabled>Select Smoking</option>
              <option value="Never">Never smoker</option>
              <option value="Former">Former smoker</option>
              <option value="Current">Current smoker</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Physically Active?</label>
            <select
              required
              value={formData.physically_active ?? ""}
              onChange={(e) => onChange("physically_active", e.target.value as YesNo)}
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-white text-sm focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
            >
              <option value="" disabled>Select</option>
              <option value="Yes">Yes</option>
              <option value="No">No</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Hypertension History?</label>
            <select
              required
              value={formData.hypertension_history ?? ""}
              onChange={(e) => onChange("hypertension_history", e.target.value as YesNo)}
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-white text-sm focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
            >
              <option value="" disabled>Select</option>
              <option value="Yes">Yes</option>
              <option value="No">No</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">High Cholesterol History?</label>
            <select
              required
              value={formData.high_cholesterol_history ?? ""}
              onChange={(e) => onChange("high_cholesterol_history", e.target.value as YesNo)}
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-white text-sm focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
            >
              <option value="" disabled>Select</option>
              <option value="Yes">Yes</option>
              <option value="No">No</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Diabetes Status?</label>
            <select
              required
              value={formData.diabetes_status ?? ""}
              onChange={(e) => onChange("diabetes_status", e.target.value as YesNo)}
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-white text-sm focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
            >
              <option value="" disabled>Select</option>
              <option value="Yes">Yes</option>
              <option value="No">No</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">History of Stroke?</label>
            <select
              required
              value={formData.stroke_history ?? ""}
              onChange={(e) => onChange("stroke_history", e.target.value as YesNo)}
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-white text-sm focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
            >
              <option value="" disabled>Select</option>
              <option value="Yes">Yes</option>
              <option value="No">No</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Family History of CHD?</label>
            <select
              required
              value={formData.family_history_chd ?? ""}
              onChange={(e) => onChange("family_history_chd", e.target.value as YesNo)}
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-white text-sm focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
            >
              <option value="" disabled>Select</option>
              <option value="Yes">Yes</option>
              <option value="No">No</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">General Health Self-Rating</label>
            <select
              required
              value={formData.general_health ?? ""}
              onChange={(e) => handleNumChange("general_health", e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-white text-sm focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
            >
              <option value="" disabled>Select Self-Rating</option>
              <option value="1">1: Excellent</option>
              <option value="2">2: Very good</option>
              <option value="3">3: Good</option>
              <option value="4">4: Fair</option>
              <option value="5">5: Poor</option>
            </select>
          </div>
        </div>
      </div>

      {/* Section 5: Cardiac Symptoms */}
      <div className="p-6 rounded-2xl bg-slate-900/50 border border-slate-800/80 space-y-4">
        <div className="flex items-center gap-2.5 pb-3 border-b border-slate-800">
          <AlertTriangle className="w-5 h-5 text-amber-400" />
          <div>
            <h3 className="text-sm font-semibold text-white">5. Cardiac Symptoms</h3>
            <p className="text-xs text-slate-400">Chest pain presentation, severity, and exertional dyspnea</p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Chest Pain Presentation</label>
            <select
              required
              value={formData.chest_pain_type ?? ""}
              onChange={(e) => onChange("chest_pain_type", e.target.value as ChestPainType)}
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-white text-sm focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
            >
              <option value="" disabled>Select Chest Pain Type</option>
              <option value="No pain">No pain</option>
              <option value="Non-exertional">Non-exertional pain</option>
              <option value="Exertional">Exertional pain</option>
              <option value="Typical angina">Typical angina</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Severe Chest Pain?</label>
            <select
              required
              value={formData.severe_chest_pain ?? ""}
              onChange={(e) => onChange("severe_chest_pain", e.target.value as YesNo)}
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-white text-sm focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
            >
              <option value="" disabled>Select</option>
              <option value="Yes">Yes</option>
              <option value="No">No</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Shortness of Breath on Exertion?
            </label>
            <select
              required
              value={formData.sob_on_exertion ?? ""}
              onChange={(e) => onChange("sob_on_exertion", e.target.value as YesNo)}
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-white text-sm focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
            >
              <option value="" disabled>Select</option>
              <option value="Yes">Yes</option>
              <option value="No">No</option>
            </select>
          </div>
        </div>
      </div>

      {/* Submit Button */}
      <div className="pt-2">
        <button
          type="submit"
          disabled={isLoading}
          className="w-full py-4 rounded-xl font-semibold text-sm flex items-center justify-center gap-2.5 transition-all bg-gradient-to-r from-rose-600 via-red-600 to-amber-600 hover:from-rose-500 hover:via-red-500 hover:to-amber-500 text-white shadow-lg shadow-rose-950/50 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
        >
          {isLoading ? (
            <>
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              <span>Evaluating Patient via Two-Stage Cascade...</span>
            </>
          ) : (
            <>
              <Activity className="w-4 h-4" />
              <span>Predict Heart Disease Risk</span>
            </>
          )}
        </button>
      </div>
    </form>
  );
};

