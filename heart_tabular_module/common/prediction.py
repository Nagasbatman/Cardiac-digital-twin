"""
prediction.py — The result every module's `predict()` returns.

Exact copy of the original common/prediction.py.
"""

from dataclasses import dataclass, field, fields
from typing import Any, Optional

import numpy as np

# Outcome of the module's safety gates
ACCEPTED = "accepted"   # passed every gate: the result can be reported as is
REVIEW = "review"       # a clinician must look: unusual patient profile the model did not score
REJECTED = "rejected"   # not an input this model can score


@dataclass
class Prediction:
    """
    organ        "heart"
    modality     "tabular"
    status       ACCEPTED, REVIEW or REJECTED
    label        risk band: "Low Risk" / "Medium Risk" / "High Risk". None when not scored.
    probability  P(heart disease). None when not scored (anomaly-gated).
    positive     screen is positive (refer). probability >= cost-optimal threshold. None when not scored.
    explanation  the inputs that moved this patient's probability most vs a typical patient.
    message      one line for the user: the finding and the next step.
    details      threshold, risk_bands, model name, anomaly_flagged flag.
    """

    organ: str
    modality: str
    status: str
    label: Optional[str] = None
    probability: Optional[float] = None
    positive: Optional[bool] = None
    explanation: dict = field(default_factory=dict)
    message: str = ""
    details: dict = field(default_factory=dict)

    @property
    def scored(self) -> bool:
        """True when the model produced a probability, i.e. the input passed the anomaly gate."""
        return self.probability is not None

    def to_dict(self, arrays: bool = True) -> dict:
        """Plain Python types. arrays=False drops numpy arrays so the result goes to json.dumps."""
        return {f.name: _plain(getattr(self, f.name), arrays) for f in fields(self)}


def _plain(value: Any, arrays: bool) -> Any:
    if isinstance(value, dict):
        return {k: _plain(v, arrays) for k, v in value.items()
                if arrays or not isinstance(v, np.ndarray)}
    if isinstance(value, (list, tuple)):
        return [_plain(v, arrays) for v in value]
    if isinstance(value, np.ndarray):
        return value
    if isinstance(value, np.generic):
        return value.item()
    return value
