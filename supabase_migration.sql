-- MathGuide Bénin — Table de progression par compétence
-- À appliquer via Supabase (SQL editor ou `supabase db push` / apply_migration)

create table if not exists eleves (
  eleve_id text primary key,
  classe text not null,
  serie text,
  total_sessions integer not null default 0,
  updated_at timestamptz not null default now()
);

create table if not exists competences_progress (
  id uuid primary key default gen_random_uuid(),
  eleve_id text not null references eleves(eleve_id) on delete cascade,
  domaine text not null,
  nb_sessions integer not null default 0,
  niveau_maitrise numeric not null default 0 check (niveau_maitrise >= 0 and niveau_maitrise <= 1),
  dernier_travail timestamptz,
  unique (eleve_id, domaine)
);

create index if not exists idx_competences_progress_eleve on competences_progress(eleve_id);

-- Row Level Security : à activer si l'app expose des clés "anon" côté client.
-- Le backend FastAPI utilise ici la clé "service_role" (ou "anon" avec policies adaptées),
-- donc RLS reste désactivé par défaut pour simplifier le démarrage.
-- alter table eleves enable row level security;
-- alter table competences_progress enable row level security;
