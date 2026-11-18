"""SQLAlchemy ORM models mapped to the pulse schema tables.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from backend.db.session import Base


class Patient(Base):
    """Patient registry supporting isolated external identifiers across modalities."""
    __tablename__ = "patients"
    __table_args__ = (
        UniqueConstraint("source_system", "patient_identifier", name="uq_patients_source_identifier"),
        {"schema": "pulse"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    patient_identifier = Column(String(128), nullable=True)
    source_system = Column(String(64), nullable=False, default="ANONYMOUS", server_default="ANONYMOUS")
    demographics = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=text("now()"), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), server_default=text("now()"), nullable=False)

    analysis_runs = relationship("AnalysisRun", back_populates="patient", cascade="all, delete-orphan")


class AnalysisRun(Base):
    """Central audit table tracking execution runs across all modules."""
    __tablename__ = "analysis_runs"
    __table_args__ = {"schema": "pulse"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    patient_id = Column(UUID(as_uuid=True), ForeignKey("pulse.patients.id", ondelete="SET NULL"), nullable=True, index=True)
    module_type = Column(String(32), nullable=False, index=True)  # 'mri', 'tabular_risk', 'cardio_twin'
    status = Column(String(32), nullable=False, default="SUCCESS", server_default="SUCCESS")
    execution_time_ms = Column(Float, nullable=True)
    metadata_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=text("now()"), nullable=False, index=True)

    patient = relationship("Patient", back_populates="analysis_runs")
    mri_analysis = relationship("MriAnalysis", back_populates="run", uselist=False, cascade="all, delete-orphan")
    risk_assessment = relationship("RiskAssessment", back_populates="run", uselist=False, cascade="all, delete-orphan")
    simulation_run = relationship("SimulationRun", back_populates="run", uselist=False, cascade="all, delete-orphan")


class MriAnalysis(Base):
    """Module 1: Volumetric cardiac MRI segmentation and classification results."""
    __tablename__ = "mri_analyses"
    __table_args__ = (
        UniqueConstraint("run_id", name="uq_mri_analyses_run_id"),
        CheckConstraint("confidence IS NULL OR (confidence >= 0.0 AND confidence <= 100.0)", name="ck_mri_analyses_confidence"),
        {"schema": "pulse"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    run_id = Column(UUID(as_uuid=True), ForeignKey("pulse.analysis_runs.id", ondelete="CASCADE"), nullable=False, unique=True)
    predicted_class = Column(String(32), nullable=False, index=True)
    confidence = Column(Float, nullable=True)
    class_probabilities = Column(JSONB, nullable=True)
    biomarkers = Column(JSONB, nullable=True)
    voxel_metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=text("now()"), nullable=False)

    run = relationship("AnalysisRun", back_populates="mri_analysis")


class RiskAssessment(Base):
    """Module 2: CDC NHANES calibrated heart disease risk predictions."""
    __tablename__ = "risk_assessments"
    __table_args__ = (
        UniqueConstraint("run_id", name="uq_risk_assessments_run_id"),
        CheckConstraint("risk_probability >= 0.0 AND risk_probability <= 1.0", name="ck_risk_assessments_risk_probability"),
        CheckConstraint("threshold >= 0.0 AND threshold <= 1.0", name="ck_risk_assessments_threshold"),
        {"schema": "pulse"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    run_id = Column(UUID(as_uuid=True), ForeignKey("pulse.analysis_runs.id", ondelete="CASCADE"), nullable=False, unique=True)
    risk_label = Column(String(64), nullable=False, index=True)
    risk_probability = Column(Float, nullable=False)
    threshold = Column(Float, nullable=False)
    positive = Column(Boolean, nullable=False)
    input_features = Column(JSONB, nullable=False)
    contributing_factors = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=text("now()"), nullable=False)

    run = relationship("AnalysisRun", back_populates="risk_assessment")


class SimulationRun(Base):
    """Module 3: CardioSim lumped-parameter ODE simulation runs."""
    __tablename__ = "simulation_runs"
    __table_args__ = (
        UniqueConstraint("run_id", name="uq_simulation_runs_run_id"),
        {"schema": "pulse"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    run_id = Column(UUID(as_uuid=True), ForeignKey("pulse.analysis_runs.id", ondelete="CASCADE"), nullable=False, unique=True)
    session_id = Column(String(128), nullable=True, index=True)
    scenario_name = Column(String(256), nullable=False)
    scenario_kind = Column(String(64), nullable=False)
    preset_name = Column(String(128), nullable=False, index=True)
    parameters = Column(JSONB, nullable=False)
    metrics = Column(JSONB, nullable=False)
    deltas = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=text("now()"), nullable=False)

    run = relationship("AnalysisRun", back_populates="simulation_run")
