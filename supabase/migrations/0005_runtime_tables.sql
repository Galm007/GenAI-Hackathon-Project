create table public.evaluation_runs (
  id                  uuid primary key default gen_random_uuid(),
  session_id          text not null,                       -- anonymous browser session id (no auth needed for the demo)
  created_at          timestamptz not null default now(),
  expires_at          timestamptz not null default now() + interval '24 hours',
  status              text not null default 'running' check (status in ('running','complete','failed')),
  school_slug         text references public.universities_cds (slug),
  intended_major      text,
  major_category      text,
  -- redacted artifacts only: the raw PDF and essay PII never reach this table
  intake              jsonb,     -- RawApplicantInputs minus file bytes
  dossier             jsonb,
  grade               jsonb,
  metrics             jsonb,
  school_rubric       jsonb,
  institutional_brief jsonb,
  twins               jsonb,
  baseline            jsonb,
  twin_analysis       jsonb,
  debate              jsonb,
  probability         jsonb,
  scoring_inputs      jsonb,     -- frozen ScoringInputs so /api/what-if can recompute without the graph
  counterfactuals     jsonb,
  delta_report        jsonb,
  profile_embedding   extensions.vector(1536),
  event_log           jsonb not null default '[]'::jsonb   -- full SSE log → DEMO_MODE replay
);
create index evaluation_runs_session_idx on public.evaluation_runs (session_id, created_at desc);
create index evaluation_runs_expiry_idx  on public.evaluation_runs (expires_at);

create table public.web_research_cache (
  query_hash   text primary key,         -- sha256(slug|query)
  school_slug  text,
  query        text not null,
  results      jsonb not null,           -- Tavily results [{url,title,content,score,published_date}]
  fetched_at   timestamptz not null default now()
);
create index web_research_cache_slug_idx on public.web_research_cache (school_slug, fetched_at desc);
