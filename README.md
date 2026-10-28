# PulseTwin: Cardiac Digital Twin for Unified Cardiac Segmentation, Diagnosis, and Few-Shot Cross-Modality Adaptation

PulseTwin reads one short-axis cardiac MRI study and returns segmentation, cardiomyopathy diagnosis, and a structured clinical report in a single pass.

---

## Abstract

Cardiac image analysis requires accurate ventricular segmentation, disease classification, and structured clinical reporting; these tasks are typically handled by separate models, limiting clinical deployment. To address this, we introduce PULSE, a unified three-task framework that performs: 

1. **Ventricular Segmentation:** Uses a DINOv2 Vision Transformer (ViT-B/14) backbone with a Dense Prediction Transformer (DPT) decoder and deep supervision.
2. **Cardiomyopathy Diagnosis:** Via a 23-dimensional clinical biomarker vector fed to a Random Forest classifier.
3. **Structured Clinical Reporting:** Populates a predefined report with measured indices and rule-based abnormality flags using deterministic, rule-driven templates.

Additionally, the model takes 2.5D inputs (three adjacent short-axis slices) and is evaluated via a 5-fold stratified ensemble. With extensive experiments on the ACDC benchmark, PULSE achieves a mean Dice of 88.8% (RV: 90.3%, Myo: 84.7%, LV: 91.6%, HD95 ≤ 4.6 mm), 90.0% patient-level diagnostic accuracy (macro-AUC 0.982), and 92.7% clinical flag agreement in the generated reports (LVEF MAE 3.09%, within inter-observer tolerance). Without retraining, PULSE achieves 85.3% mean Dice on M&Ms-2 and 88.1% LV Dice on Sunnybrook MRI. Few-shot fine-tuning on CAMUS echocardiography samples yields a mean Dice of 73.2%, showing strong cross-modality transfer from cardiac MRI priors.

---

## Key Contributions

- A unified framework delivering segmentation, cardiomyopathy diagnosis, and structured reporting from a single cardiac MRI study.
- A foundation-model segmentation backbone (DINOv2 ViT-B/14) with a DPT decoder, a two-stage fine-tuning curriculum, and deep supervision.
- An interpretable, biomarker-driven diagnosis stage decoupled from the image encoder.
- Strong zero-shot generalization across scanner vendors and few-shot cross-modality transfer to echocardiography.

---

## Installation

PULSE runs on Linux, macOS, and Windows. A GPU is recommended for training; inference also runs on CPU.

**1. Create and activate environment:**
```bash
conda create -n pulse python=3.10 -y
conda activate pulse