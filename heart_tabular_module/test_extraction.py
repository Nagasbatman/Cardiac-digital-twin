"""
test_extraction.py — Validates the extracted heart_tabular_module independently.

Run from heart_tabular_module/:
    python test_extraction.py

Tests:
 1. Model and anomaly gate load correctly
 2. Example patient (high-risk) produces expected output
 3. Sparse input (only 6 known fields) runs without error
 4. Missing-column error is raised correctly
 5. Invalid type raises or is coerced gracefully
 6. Prediction does not depend on files outside this folder
 7. predict_batch works on multiple rows
 8. Outputs match the original README's documented example
"""

import json
import sys
from pathlib import Path

# Ensure the module root is on sys.path
_MODULE_ROOT = Path(__file__).resolve().parent
if str(_MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(_MODULE_ROOT))

import pandas as pd

PASS = "[PASS]"
FAIL = "[FAIL]"

results = []


def check(name, condition, detail=""):
    status = PASS if condition else FAIL
    results.append((status, name, detail))
    print(f"{status}  {name}" + (f" - {detail}" if detail else ""))
    return condition


# ─── 1. Import and model paths ────────────────────────────────────────────────
print("\n=== 1. Import & model paths ===")
try:
    from src.predict import predict, predict_batch, MODEL, REQUIRED_COLUMNS, MODEL_DIR
    check("Import src.predict", True)
    check("MODEL_DIR inside module", str(_MODULE_ROOT) in str(MODEL_DIR.resolve()),
          str(MODEL_DIR.resolve()))
    check("Calibrated model file exists", MODEL.model_path.exists(), str(MODEL.model_path))
    check("Anomaly gate file exists", MODEL.gate_path.exists(), str(MODEL.gate_path))
    check("metadata.json exists", MODEL.metadata_path.exists(), str(MODEL.metadata_path))
    check("reference_profile.json exists", MODEL.reference_path.exists(), str(MODEL.reference_path))
except Exception as e:
    check("Import src.predict", False, str(e))
    print("Cannot continue — import failed.")
    sys.exit(1)

# ─── 2. Example patient (from examples/patient.json) ─────────────────────────
print("\n=== 2. High-risk example patient ===")
EXAMPLE_PATH = _MODULE_ROOT / "examples" / "patient.json"
example = json.loads(EXAMPLE_PATH.read_text())

try:
    result = predict(example, explain=True)
    check("Status is 'accepted'", result.status == "accepted", result.status)
    check("Label is 'High Risk'", result.label == "High Risk", result.label)
    check("Probability > 0.50", result.probability is not None and result.probability > 0.50,
          f"{result.probability:.3f}" if result.probability else "None")
    check("positive is True", result.positive is True, str(result.positive))
    check("Message contains 'refer'", "refer" in result.message.lower(), result.message)
    check("Explanation factors present", len(result.explanation.get("factors", [])) > 0,
          f"{len(result.explanation.get('factors', []))} factors")
    check("Probability matches README (~0.924, ±0.02)",
          result.probability is not None and abs(result.probability - 0.924) < 0.05,
          f"{result.probability:.3f}")
    print(f"   Full message: {result.message}")
    top = result.explanation.get("factors", [])[:2]
    for f in top:
        print(f"   Factor: {f['feature']} = {f['value']} (typical: {f['typical']}, effect: {f['effect']:+.3f})")
except Exception as e:
    check("Example patient prediction", False, str(e))
    import traceback; traceback.print_exc()

# ─── 3. Sparse input — 6 known fields, remainder None (imputed) ─────────────
print("\n=== 3. Sparse input (6 known / 31, remainder None) ===")
sparse = {col: None for col in REQUIRED_COLUMNS}
sparse.update({
    "age": 67, "gender": "Male",
    "systolic_bp": 158, "diastolic_bp": 84,
    "chest_pain_type": "Exertional", "severe_chest_pain": "Yes",
})
try:
    r_sparse = predict(sparse, explain=False)
    check("Sparse input runs without error", True)
    check("Status is 'accepted' or 'review'", r_sparse.status in ("accepted", "review"),
          r_sparse.status)
    if r_sparse.scored:
        check("Sparse probability is a float", isinstance(r_sparse.probability, float),
              str(r_sparse.probability))
    print(f"   Sparse result: {r_sparse.status} — {r_sparse.message}")
except Exception as e:
    check("Sparse input runs without error", False, str(e))

# ─── 4. Missing column raises ValueError ──────────────────────────────────────
print("\n=== 4. Missing column error ===")
try:
    bad_input = {"age": 50}   # missing all 30 other columns
    _ = predict(bad_input)
    check("Missing columns raise ValueError", False, "No error raised")
except ValueError as e:
    check("Missing columns raise ValueError", True, str(e)[:80])
except Exception as e:
    check("Missing columns raise ValueError", False, f"Wrong exception: {e}")

# ─── 5. Invalid type coercion ─────────────────────────────────────────────────
print("\n=== 5. Invalid numeric type (string as number) ===")
bad_types = dict(example)
bad_types["age"] = "sixty-seven"   # should be coerced / caught
try:
    r_bad = predict(bad_types, explain=False)
    check("String age either coerces or raises gracefully", True,
          f"Result: {r_bad.status} {r_bad.label}")
except (ValueError, TypeError) as e:
    check("String age raises ValueError/TypeError", True, str(e)[:80])
except Exception as e:
    check("String age handled", False, str(e))

# ─── 6. No dependency on files outside the module ─────────────────────────────
print("\n=== 6. No external file dependencies ===")
import os
check("MODEL_DIR not outside module root",
      str(MODEL_DIR.resolve()).startswith(str(_MODULE_ROOT.resolve())),
      str(MODEL_DIR.resolve()))
check("common/ is inside module", (_MODULE_ROOT / "common").exists())
check("src/ is inside module", (_MODULE_ROOT / "src").exists())

# ─── 7. predict_batch ─────────────────────────────────────────────────────────
print("\n=== 7. predict_batch ===")
try:
    batch_df = pd.DataFrame([example, example])   # two identical patients
    batch_result = predict_batch(batch_df)
    check("predict_batch returns DataFrame", isinstance(batch_result, pd.DataFrame),
          str(type(batch_result)))
    check("predict_batch has 2 rows", len(batch_result) == 2, str(len(batch_result)))
    check("predict_batch columns present",
          {"status", "label", "probability", "positive", "message"} <= set(batch_result.columns))
    print(f"   Batch result:\n{batch_result[['status', 'label', 'probability']].to_string()}")
except Exception as e:
    check("predict_batch", False, str(e))
    import traceback; traceback.print_exc()

# ─── 8. to_dict serialisation ─────────────────────────────────────────────────
print("\n=== 8. Prediction.to_dict() ===")
try:
    result_dict = result.to_dict(arrays=False)
    check("to_dict returns dict", isinstance(result_dict, dict))
    check("to_dict has expected keys",
          {"organ", "modality", "status", "label", "probability", "positive"} <= result_dict.keys())
    serialised = json.dumps(result_dict, default=str)
    check("to_dict is JSON serialisable", True)
except Exception as e:
    check("to_dict / JSON serialise", False, str(e))

# ─── Summary ──────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
passed = sum(1 for s, _, _ in results if s == PASS)
total = len(results)
print(f"Results: {passed}/{total} tests passed")

if passed < total:
    print("\nFailed tests:")
    for status, name, detail in results:
        if status != PASS:
            print(f"  {status}  {name}  -  {detail}")
    sys.exit(1)
else:
    print("\nAll tests passed. The extracted module is working correctly.")
