"""
common — Shared inference infrastructure for the extracted heart tabular module.
Exact copy of the original common/ package, scoped to this standalone folder.
"""

from .prediction import ACCEPTED, REJECTED, REVIEW, Prediction

__all__ = ["ACCEPTED", "REJECTED", "REVIEW", "Prediction"]
