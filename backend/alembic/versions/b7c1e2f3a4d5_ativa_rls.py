"""ativa RLS nas tabelas (Supabase)

No Supabase, tabela sem RLS fica aberta a qualquer um com a chave pública pela API REST.
Com RLS ligado e sem políticas, a API REST não acessa nada; o backend conecta como dono
das tabelas e não é afetado. Em SQLite esta migração não faz nada.

Revision ID: b7c1e2f3a4d5
Revises: ad6eee9869aa
Create Date: 2026-11-01 13:35:00
"""
from alembic import op
import sqlalchemy as sa


revision = 'b7c1e2f3a4d5'
down_revision = 'ad6eee9869aa'
branch_labels = None
depends_on = None


def _public_tables() -> list[str]:
    rows = op.get_bind().execute(sa.text(
        "select tablename from pg_tables where schemaname = 'public'"
    ))
    return [r[0] for r in rows]


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for table in _public_tables():
        op.execute(f'alter table public."{table}" enable row level security')


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for table in _public_tables():
        op.execute(f'alter table public."{table}" disable row level security')
