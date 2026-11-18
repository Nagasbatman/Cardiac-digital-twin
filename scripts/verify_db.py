"""Verify all pulse database objects, constraints, foreign keys, and indexes.
"""
from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
raw = os.getenv("DATABASE_URL", "")
db_url = raw.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(db_url)
with engine.connect() as conn:
    print("=== 1. VERIFY TABLES IN PULSE SCHEMA ===")
    tables = conn.execute(text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'pulse'
        ORDER BY table_name;
    """)).fetchall()
    for t in tables:
        print("Table:", t[0])

    print("\n=== 2. VERIFY ALEMBIC VERSION ===")
    versions = conn.execute(text("SELECT version_num FROM alembic_version;")).fetchall()
    for v in versions:
        print("Alembic Version:", v[0])

    print("\n=== 3. VERIFY CONSTRAINTS (PK, FK, UNIQUE, CHECK) ===")
    constraints = conn.execute(text("""
        SELECT 
            tc.table_name, 
            tc.constraint_name, 
            tc.constraint_type
        FROM information_schema.table_constraints tc
        WHERE tc.table_schema = 'pulse'
        ORDER BY tc.table_name, tc.constraint_type, tc.constraint_name;
    """)).fetchall()
    for c in constraints:
        print(f"{c[0]}: [{c[2]}] {c[1]}")

    print("\n=== 4. VERIFY CHECK CONSTRAINTS CLAUSES ===")
    checks = conn.execute(text("""
        SELECT 
            tc.table_name, 
            cc.constraint_name, 
            cc.check_clause
        FROM information_schema.check_constraints cc
        JOIN information_schema.table_constraints tc 
            ON cc.constraint_name = tc.constraint_name
        WHERE tc.table_schema = 'pulse';
    """)).fetchall()
    for chk in checks:
        print(f"{chk[0]}.{chk[1]}: {chk[2]}")

    print("\n=== 5. VERIFY FOREIGN KEYS ===")
    fks = conn.execute(text("""
        SELECT
            kcu.table_name,
            kcu.column_name,
            ccu.table_schema AS foreign_table_schema,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name,
            rc.delete_rule
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
          ON tc.constraint_name = kcu.constraint_name
          AND tc.table_schema = kcu.table_schema
        JOIN information_schema.referential_constraints AS rc
          ON tc.constraint_name = rc.constraint_name
        JOIN information_schema.constraint_column_usage AS ccu
          ON rc.unique_constraint_name = ccu.constraint_name
          AND rc.unique_constraint_schema = ccu.table_schema
        WHERE tc.table_schema = 'pulse';
    """)).fetchall()
    for fk in fks:
        print(f"{fk[0]}.{fk[1]} -> {fk[2]}.{fk[3]}.{fk[4]} (ON DELETE {fk[5]})")

    print("\n=== 6. VERIFY INDEXES IN PULSE SCHEMA ===")
    indexes = conn.execute(text("""
        SELECT 
            tablename, 
            indexname, 
            indexdef
        FROM pg_indexes 
        WHERE schemaname = 'pulse'
        ORDER BY tablename, indexname;
    """)).fetchall()
    for idx in indexes:
        print(f"{idx[0]}: {idx[1]}")

