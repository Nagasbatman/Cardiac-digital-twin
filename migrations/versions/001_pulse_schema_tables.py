"""Create pulse schema and tables

Revision ID: 001_create_pulse_schema_and_tables
Revises: 
Create Date: 2026-11-18 14:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_pulse_schema_tables'
down_revision = None  # Verified: Initial migration in repository & database
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Explicit schema creation (fails if 'pulse' already exists, preventing accidental reuse)
    op.execute("CREATE SCHEMA pulse")

    # 2. Table: pulse.patients
    op.create_table(
        'patients',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('patient_identifier', sa.String(length=128), nullable=True),
        sa.Column('source_system', sa.String(length=64), nullable=False, server_default='ANONYMOUS'),
        sa.Column('demographics', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('source_system', 'patient_identifier', name='uq_patients_source_identifier'),
        schema='pulse'
    )

    # 3. Table: pulse.analysis_runs (Authoritative patient association lives here)
    op.create_table(
        'analysis_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pulse.patients.id', ondelete='SET NULL'), nullable=True),
        sa.Column('module_type', sa.String(length=32), nullable=False),  # 'mri', 'tabular_risk', 'cardio_twin'
        sa.Column('status', sa.String(length=32), nullable=False, server_default='SUCCESS'),
        sa.Column('execution_time_ms', sa.Float(), nullable=True),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        schema='pulse'
    )
    op.create_index('ix_pulse_analysis_runs_created_at', 'analysis_runs', ['created_at'], schema='pulse')
    op.create_index('ix_pulse_analysis_runs_module_type', 'analysis_runs', ['module_type'], schema='pulse')
    op.create_index('ix_pulse_analysis_runs_patient_id', 'analysis_runs', ['patient_id'], schema='pulse')

    # 4. Table: pulse.mri_analyses (Module 1)
    op.create_table(
        'mri_analyses',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pulse.analysis_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('predicted_class', sa.String(length=32), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('class_probabilities', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('biomarkers', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('voxel_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        # Exactly one MRI analysis per execution run
        sa.UniqueConstraint('run_id', name='uq_mri_analyses_run_id'),
        sa.CheckConstraint('confidence IS NULL OR (confidence >= 0.0 AND confidence <= 100.0)', name='ck_mri_analyses_confidence'),
        schema='pulse'
    )
    op.create_index('ix_pulse_mri_analyses_predicted_class', 'mri_analyses', ['predicted_class'], schema='pulse')

    # 5. Table: pulse.risk_assessments (Module 2)
    op.create_table(
        'risk_assessments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pulse.analysis_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('risk_label', sa.String(length=64), nullable=False),
        sa.Column('risk_probability', sa.Float(), nullable=False),
        sa.Column('threshold', sa.Float(), nullable=False),
        sa.Column('positive', sa.Boolean(), nullable=False),
        sa.Column('input_features', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('contributing_factors', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        # Exactly one risk assessment per execution run
        sa.UniqueConstraint('run_id', name='uq_risk_assessments_run_id'),
        # Probability & threshold bounded in [0.0, 1.0]
        sa.CheckConstraint('risk_probability >= 0.0 AND risk_probability <= 1.0', name='ck_risk_assessments_risk_probability'),
        sa.CheckConstraint('threshold >= 0.0 AND threshold <= 1.0', name='ck_risk_assessments_threshold'),
        schema='pulse'
    )
    op.create_index('ix_pulse_risk_assessments_risk_label', 'risk_assessments', ['risk_label'], schema='pulse')

    # 6. Table: pulse.simulation_runs (Module 3)
    op.create_table(
        'simulation_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pulse.analysis_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('session_id', sa.String(length=128), nullable=True),
        sa.Column('scenario_name', sa.String(length=256), nullable=False),
        sa.Column('scenario_kind', sa.String(length=64), nullable=False),
        sa.Column('preset_name', sa.String(length=128), nullable=False),
        sa.Column('parameters', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('metrics', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('deltas', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        # Exactly one simulation outcome per execution run
        sa.UniqueConstraint('run_id', name='uq_simulation_runs_run_id'),
        schema='pulse'
    )
    op.create_index('ix_pulse_simulation_runs_session_id', 'simulation_runs', ['session_id'], schema='pulse')
    op.create_index('ix_pulse_simulation_runs_preset_name', 'simulation_runs', ['preset_name'], schema='pulse')


def downgrade() -> None:
    # 1. Drop the five tables in reverse dependency order
    op.drop_table('simulation_runs', schema='pulse')
    op.drop_table('risk_assessments', schema='pulse')
    op.drop_table('mri_analyses', schema='pulse')
    op.drop_table('analysis_runs', schema='pulse')
    op.drop_table('patients', schema='pulse')

    # 2. Drop schema strictly without CASCADE (protects any unrelated objects)
    op.execute("DROP SCHEMA pulse")
