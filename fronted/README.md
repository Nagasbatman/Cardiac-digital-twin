# PULSE Web Portal (Next.js 16 + TypeScript + Tailwind CSS)

Modern medical-research dashboard for the **Digital Twin-Driven Cardiovascular Risk Prediction System**.

---

## 1. Multi-Module Navigation

The frontend provides unified navigation across all three platform modules:

1. **Module I: Cardiac MRI Analysis** (`/`)
   - 2.5D paired and 4D cine MRI short-axis slice segmentation with 4-fold DINOv2 ensemble.
   - Interactive volumetric slice slider and multi-layer RGB anatomical overlays (RV Red, Myo Green, LV Blue).
   - 23 clinical biomarkers table with normal reference ranges and category filters.
   - ACDC 5-class cardiomyopathy diagnostic classification.

2. **Module II: Heart Disease Risk Prediction** (`/heart-prediction`)
   - Tabular demographic, hemodynamic, laboratory, and symptomatic risk prediction.
   - Categorized input forms with instant sample patient pre-fill.
   - Prediction results, risk levels, and contributing feature insights.

3. **Module III: Cardiovascular Digital Twin & CardioSim Simulation** (`/cardiovascular-twin`)
   - **Area 1 (Telemetry & Context)**: Real-time API telemetry, research prototype indicator, and HIPAA de-identification notices.
   - **Area 2 (Patient Cohort Explorer)**: 1,500-patient MIMIC-IV cohort search with instant quick-select curated clinical profiles (Young baseline, adult hypertensive, elderly diabetic, complex multi-visit).
   - **Area 3 (Current Cardiovascular State)**: Categorized observation cards (Blood Pressure, Glycemic Control, Renal Function, Lipid Profile).
   - **Area 4 (Recorded Clinical History)**: Interactive SVG trend charts across longitudinal visits and paginated observation history.
   - **Area 5 (What-if Scenario Engine)**:
     - Scientific parameter provenance table distinguishing clinical measurements from ODE parameters (`MEASURED`, `ESTIMATED`, `ASSUMED`, `UNAVAILABLE`).
     - Reference baseline selector (Healthy Adult, Hypertension, Heart Failure, etc.).
     - Bound-checked slider controls for simulation inputs (`hr`, `contract`, `resist`, `compl`).
     - Real-time simulation execution via live CardioSim engine.
     - Key Hemodynamic KPI cards (Cardiac Output, Stroke Volume, Mean Arterial Pressure).
     - Color-coded Left Ventricular Ejection Fraction (LVEF) continuum progress bar.
     - Side-by-side metric comparison table with absolute and percentage deltas against baseline.

---

## 2. Configuration & Environment Variables

Create or update `.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8001
```

> [!IMPORTANT]
> The unified backend runs on port 8001 to avoid colliding with CardioSim on port 8000.

---

## 3. Development & Build

### Development Server
```bash
npm run dev
```
Open [http://localhost:3000](http://localhost:3000).

### Production Build
```bash
npm run build
npm run start
```
Compiles with Next.js 16 App Router and static export compatibility.
