"""Typed dataclasses for CardioSim API responses.

Field names are preserved exactly as returned by the API (e.g. ``map_val``,
``compare_preset``).  No field is renamed or reinterpreted here.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class PresetInfo:
    """One entry from ``GET /api/presets``."""

    name: str
    hr: float
    contract: float
    resist: float
    compl: float
    desc: str
    category: str

    @classmethod
    def from_api(cls, name: str, raw: dict[str, Any]) -> "PresetInfo":
        return cls(
            name=name,
            hr=float(raw["hr"]),
            contract=float(raw["contract"]),
            resist=float(raw["resist"]),
            compl=float(raw["compl"]),
            desc=str(raw["desc"]),
            category=str(raw["category"]),
        )


@dataclass
class SimMetrics:
    """Scalar and array metrics from a single simulation run.

    Scalar fields (``co``, ``sv``, ``sys``, ``dia``, ``map_val``, ``pp``,
    ``ef``, ``hr``) are ``float``.  Array fields (``lv_vol``, ``lvp``,
    ``lvof``, ``lvp_full``) are ``list[float]``.
    """

    co: float
    sv: float
    sys: float
    dia: float
    map_val: float  # preserved: API uses map_val, not map
    pp: float
    ef: float
    hr: float
    lv_vol: list[float]
    lvp: list[float]
    lvof: list[float]
    lvp_full: list[float]

    @classmethod
    def from_api(cls, raw: dict[str, Any]) -> "SimMetrics":
        return cls(
            co=float(raw["co"]),
            sv=float(raw["sv"]),
            sys=float(raw["sys"]),
            dia=float(raw["dia"]),
            map_val=float(raw["map_val"]),
            pp=float(raw["pp"]),
            ef=float(raw["ef"]),
            hr=float(raw["hr"]),
            lv_vol=list(raw["lv_vol"]),
            lvp=list(raw["lvp"]),
            lvof=list(raw["lvof"]),
            lvp_full=list(raw["lvp_full"]),
        )


@dataclass
class SimResult:
    """One simulation result (primary or comparison)."""

    t: list[float]
    X: list[list[float]]
    ecg: list[float]
    preset: str
    params: dict[str, Any]
    metrics: SimMetrics
    rr: list[float] | None

    @classmethod
    def from_api(cls, raw: dict[str, Any]) -> "SimResult":
        return cls(
            t=list(raw["t"]),
            X=list(raw["X"]),
            ecg=list(raw["ecg"]),
            preset=str(raw["preset"]),
            params=dict(raw["params"]),
            metrics=SimMetrics.from_api(raw["metrics"]),
            rr=list(raw["rr"]) if raw.get("rr") is not None else None,
        )


@dataclass
class SimResponse:
    """Full response from ``POST /api/simulate``.

    ``comparison`` is ``None`` when no ``compare_preset`` was requested (or
    the preset was not found).
    """

    primary: SimResult
    comparison: SimResult | None

