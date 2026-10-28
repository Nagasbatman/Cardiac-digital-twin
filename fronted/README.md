# PulseTwin Web Portal (Next.js + TypeScript)

Modern medical-research dashboard for **PULSE: Cardiac MRI Segmentation, Biomarker Extraction, and Cardiomyopathy Diagnosis**.

---

## Architecture & Integration

This frontend interface operates as an independent client for the PULSE deep learning engine without modifying any existing machine learning pipelines, checkpoints, or the Gradio interface:

- **Frontend (`fronted/`)**: Next.js 16 (App Router) + TypeScript + Tailwind CSS + Lucide Icons.
- **Backend API Adapter (`api_server.py`)**: FastAPI REST service running on port 8000. Reuses the 4-fold ViT-B/14 DINOv2 ensemble (`folds_vdino/fold_{0..3}`) and Random Forest classifier (`diagnosis_classifier.joblib`) from `demo/app.py`.
- **Original Gradio Application (`demo/app.py`)**: Remains 100% untouched and runs independently on port 7860.

---

## Core Supported Clinical Functions

1. **Paired 3D Volume Upload**: Upload paired End-Diastole (ED) and End-Systole (ES) short-axis NIfTI scans (`.nii` and `.nii.gz`).
2. **4D Cine MRI Temporal Study**: Upload 4D temporal cine MRI with configurable ED and ES frame index pickers.
3. **Interactive Volumetric Segmentation Viewer**:
   - Scrub base-to-apex short-axis slices with a dedicated slider.
   - Distinct anatomical color overlays: **RV = Red (`#dc2828`)**, **Myocardium = Green (`#28c83c`)**, **LV = Blue (`#325ae6`)**.
   - View modes: Segmentation Overlay, Raw Grayscale MRI, and Side-by-Side Comparison.
4. **23 Clinical Biomarkers**:
   - Ventricular volumetrics (LV EDV, LV ESV, LV SV, LV EF, RV EDV, RV ESV, RV SV, RV EF).
   - Myocardial mass & wall dimensions (LVM, Myo ED/ES, Mean/Max/Std wall thickness).
   - BSA-indexed parameters (LV EDVi, LV ESVi, LVMi, RV EDVi).
   - Geometric remodeling ratios (Concentricity, RV/LV EDV, ESV/EDV, RVEF/LVEF, Myo/LV).
   - Category filtering, search bar, and CSV export.
5. **ACDC 5-Class Cardiomyopathy Classification**:
   - Predicts NOR (Normal), DCM (Dilated Cardiomyopathy), HCM (Hypertrophic Cardiomyopathy), MINF (Myocardial Infarction), or RV (Abnormal RV).
   - Displays full confidence percentages and probability distribution across all 5 classes.
6. **1-Click Demo Evaluation**: Includes a fast demo button to instantly load and evaluate the bundled ACDC Patient 101 case without requiring manual file uploads.

---

## Quickstart Guide

### 1. Launch the Python API Adapter (Port 8000)

From the project root:

```bash
# Activate your python environment
.venv\Scripts\python.exe api_server.py
```

### 2. Launch the Next.js Frontend (Port 3000)

From the `fronted/` folder:

```bash
cd fronted
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### 3. Launch the Original Gradio UI (Port 7860)

The original Gradio app remains completely intact:

```bash
# From project root
.venv\Scripts\python.exe demo/app.py
```

Open [http://127.0.0.1:7860](http://127.0.0.1:7860) in your browser.

---

## Environment Variables

Configured in `fronted/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```
