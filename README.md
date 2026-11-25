# PULSE: Digital Twin-Driven Cardiovascular Risk Prediction System

A unified, multi-modal clinical research platform integrating deep learning cardiac MRI analysis, tabular cardiovascular risk prediction, and lumped-parameter cardiovascular digital twin simulations.

---

## 1. System Architecture

The system integrates three specialized cardiovascular modeling modules into a unified full-stack application:

```
+---------------------------------------------------------------------------------------------------+
|                                      PULSE Unified Application                                    |
|                                                                                                   |
|  [Next.js 16 Frontend - Port 3000]                                                                |
|  - App Router, TypeScript, Tailwind CSS, Lucide Icons                                              |
|  - Navigation across Module I, Module II, and Module III                                          |
|                                                                                                   |
|                                   |  HTTP REST Requests                                           |
|                                   v                                                               |
|                                                                                                   |
|  [FastAPI Unified Backend - Port 8001]                                                            |
|  +---------------------------------------------------------------------------------------------+  |
|  | Module I: Cardiovascular MRI Analysis                                                        |  |
|  | - ViT-B/14 DINOv2 4-fold ensemble segmentation & 23 clinical biomarkers                         |  |
|  | - ACDC 5-class cardiomyopathy Random Forest classifier                                       |  |
|  +---------------------------------------------------------------------------------------------+  |
|  | Module II: Heart Disease Tabular Risk Prediction                                             |  |
|  | - Clinical tabular demographic, laboratory, and symptomatic risk prediction                  |  |
|  +---------------------------------------------------------------------------------------------+  |
|  | Module III: Cardiovascular Digital Twin & Scenario Engine                                    |  |
|  | - Local 1,500-patient MIMIC-IV prototype cohort data loader                                  |  |
|  | - Scientific parameter provenance boundary (MEASURED, ESTIMATED, ASSUMED, UNAVAILABLE)       |  |
|  | - Interactive what-if scenario engine with baseline comparisons & delta computation          |  |
|  +---------------------------------------------------------------------------------------------+  |
|                                   |                                                               |
+-----------------------------------|---------------------------------------------------------------+
                                    | REST Client (HTTP)
                                    v
+---------------------------------------------------------------------------------------------------+
|  [External CardioSim ODE Simulation Engine - Port 8000]                                          |
|  - 0D lumped-parameter differential equation hemodynamic simulator                                |
|  - Standalone service exposing GET /api/presets and POST /api/simulate                            |
+---------------------------------------------------------------------------------------------------+
```

---

## 2. Port Allocations & Network Topology

| Component | Port | Host URL | Description |
| :--- | :--- | :--- | :--- |
| **CardioSim Engine** | `8000` | `http://localhost:8000` | External ODE simulation backend |
| **PULSE Unified Backend** | `8001` | `http://127.0.0.1:8001` | Unified FastAPI service hosting all 3 modules |
| **PULSE Next.js Frontend** | `3000` | `http://localhost:3000` | Unified web dashboard |

> [!NOTE]
> CardioSim occupies port 8000. To prevent port collisions, the PULSE unified backend runs on port 8001, and the Next.js frontend calls `NEXT_PUBLIC_API_URL=http://localhost:8001`.

---

## 3. The Three Modules

### Module 1: Cardiovascular MRI Analysis
- **Model Backbone**: 4-fold ensemble DINOv2 ViT-B/14 with Dense Prediction Transformer (DPT) decoder.
- **Biomarkers**: 23 volumetric, indexed, geometry, and myocardial wall thickness biomarkers.
- **Diagnostic Classifier**: 5-class ACDC cardiomyopathy predictor (NOR, DCM, HCM, MINF, RV).
- **Validation**: Enforces strict spatial, frame-count, patient identity, and ground-truth mask rejection rules.

### Module 2: Heart Disease Tabular Risk Prediction
- **Input Variables**: Patient demographics, hemodynamics (BP, resting HR), lab tests (HbA1c, lipids, creatinine, albuminuria, CBC), and symptom history.
- **Output**: Multiclass risk categorization and feature importance breakdown.

### Module 3: Cardiovascular Digital Twin & CardioSim Simulation
- **Cohort Dataset**: 1,500-patient prototype dataset extracted from MIMIC-IV (`cardio_twin/datasets/prototype/`).
- **Clinical History**: Longitudinally tracked blood pressures, glucose, HbA1c, creatinine, and lipid panels.
- **Scientific Provenance Boundary**:
  - Distinguishes clinical observations from mathematical simulation parameters.
  - Prevents non-physical or unvalidated mappings (e.g., blood pressure to vascular resistance without authoritative equations).
  - Categorizes all parameters as `MEASURED`, `ESTIMATED`, `ASSUMED`, or `UNAVAILABLE`.
- **Scenario Simulator**:
  - Generates population reference baselines (e.g., Healthy Adult, Hypertension, Heart Failure).
  - Runs researcher-specified interactive what-if variations with bound-checked parameters (`hr`, `contract`, `resist`, `compl`).
  - Automatically calculates absolute and relative deltas against baseline alongside key hemodynamic KPIs (CO, SV, EF continuum, BP).

---

## 4. Startup Guide (Exact Order)

### Step 1: Start the CardioSim Engine (Port 8000)
In a dedicated terminal:
```powershell
cd C:\Users\cardiac_digital_twin\CardioSim\backend
# Run with uvicorn on port 8000
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Step 2: Start the PULSE Unified Backend (Port 8001)
In a dedicated terminal:
```powershell
cd C:\Users\cardiac_digital_twin\PULSE
# Option A: Run directly without activating (recommended)
.\.venv\Scripts\python.exe api_server.py

# Option B: Activate via .bat (works without changing execution policy)
# .\.venv\Scripts\activate.bat && python api_server.py

# Option C: Enable PowerShell scripts once, then use .ps1
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
# .\.venv\Scripts\Activate.ps1 && python api_server.py
```
Verify the unified health endpoint:
```powershell
curl http://127.0.0.1:8001/api/health
```

### Step 3: Start the PULSE Next.js Frontend (Port 3000)
In a dedicated terminal:
```powershell
cd C:\Users\cardiac_digital_twin\PULSE\frontend
npm run dev
```
Open **[http://localhost:3000](http://localhost:3000)** in your browser.

---

## 5. Verification & Testing

Run all unit, API, validation, and integration tests across all three modules:

```powershell
cd C:\Users\cardiac_digital_twin\PULSE
.\.venv\Scripts\python.exe -m pytest tests/ -v
```

This runs:
- `test_validation.py`: 18 validation and clinical integrity tests for Module 1.
- `test_api_validation.py`: 5 API input validation and inference tests for Module 1.
- `test_cardio_twin_backend.py`: 11 end-to-end integration tests for Module 3 (cohort loading, observation trends, provenance boundary, live CardioSim preset simulation, what-if engine, delta calculation).
