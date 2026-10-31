export type Gender = "Female" | "Male";

export type Ethnicity =
  | "Mexican American"
  | "Non-Hispanic Black"
  | "Non-Hispanic White"
  | "Non-Hispanic Asian"
  | "Other Hispanic"
  | "Other/Multi-Racial";

export type SmokingStatus = "Never" | "Former" | "Current";

export type YesNo = "No" | "Yes";

export type ChestPainType =
  | "No pain"
  | "Non-exertional"
  | "Exertional"
  | "Typical angina";

export interface HeartTabularInput {
  age: number;
  gender: Gender;
  ethnicity: Ethnicity;
  education_level: number;
  poverty_income_ratio: number;
  bmi: number;
  waist_cm: number;
  height_cm: number;
  systolic_bp: number;
  diastolic_bp: number;
  resting_heart_rate: number;
  total_cholesterol: number;
  hdl_cholesterol: number;
  hba1c: number;
  serum_creatinine: number;
  uric_acid: number;
  albumin_creatinine_ratio: number;
  white_blood_cells: number;
  hemoglobin: number;
  rdw: number;
  smoking_status: SmokingStatus;
  physically_active: YesNo;
  hypertension_history: YesNo;
  high_cholesterol_history: YesNo;
  diabetes_status: YesNo;
  stroke_history: YesNo;
  family_history_chd: YesNo;
  general_health: number;
  chest_pain_type: ChestPainType;
  severe_chest_pain: YesNo;
  sob_on_exertion: YesNo;
}

export interface RiskFactorContribution {
  feature: string;
  impact?: string;
  direction?: string;
  patient_value?: any;
  reference_value?: any;
  description?: string;
}

export interface HeartTabularResponse {
  success: boolean;
  status: "accepted" | "review";
  label: "Low Risk" | "Medium Risk" | "High Risk" | string | null;
  probability: number | null;
  threshold: number;
  risk_bands: {
    low: string;
    medium: string;
    high: string;
  };
  positive: boolean | null;
  message: string;
  factors: RiskFactorContribution[];
  details: {
    disease: string;
    model: string;
    threshold: number;
    risk_bands: Record<string, string>;
    anomaly_flagged: boolean;
  };
  input_summary?: Partial<HeartTabularInput>;
}

