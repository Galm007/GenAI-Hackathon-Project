create table public.applicant_twins (
  id                     uuid primary key default gen_random_uuid(),

  -- provenance (no Reddit usernames are stored)
  reddit_id              text not null unique,                    -- e.g. 't3_1bx9k2' → stored as '1bx9k2'
  subreddit              text not null check (subreddit in ('collegeresults', 'TransferToTop25')),
  source_url             text not null,                           -- https://www.reddit.com/r/.../comments/<id>/
  post_created_at        timestamptz not null,
  cycle_year             smallint check (cycle_year between 2015 and 2035),   -- matriculation year
  applicant_type         public.applicant_type not null,

  -- academics
  gpa_uw                 numeric(3,2) check (gpa_uw between 0 and 4.00),
  gpa_w                  numeric(4,2) check (gpa_w between 0 and 6.00),
  gpa_w_scale            numeric(3,1),
  college_gpa            numeric(3,2) check (college_gpa between 0 and 4.00),   -- transfers
  class_rank_pct         numeric(5,4) check (class_rank_pct between 0 and 1),   -- 0.02 = top 2%
  sat_score              smallint check (sat_score between 400 and 1600),
  sat_math               smallint check (sat_math between 200 and 800),
  sat_ebrw               smallint check (sat_ebrw between 200 and 800),
  act_score              smallint check (act_score between 1 and 36),
  applied_test_optional  boolean,
  ap_count               smallint check (ap_count between 0 and 30),
  ib_diploma             boolean,
  honors_count           smallint,
  dual_enrollment_count  smallint,
  ap_scores              jsonb not null default '[]'::jsonb,   -- [{"subject":"Calc BC","score":5}]
  rigor_label            text check (rigor_label in ('most_demanding','very_demanding','demanding','average','below_average','unknown')),

  -- major
  intended_major         text,                                  -- raw text: "CS + Math double"
  major_category         text not null default 'undecided'
                         check (major_category = any (public.major_category_keys())),

  -- context (self-reported; race is kept ONLY for aggregate bias audits, never embedded or modeled)
  demographics           jsonb not null default '{}'::jsonb,
  -- {"gender":"F","race_ethnicity_raw":"...","residency_state":"CA","country":"US",
  --  "income_bracket":"80-150k","school_type":"public","first_gen":false}
  hooks                  text[] not null default '{}',
  -- subset of: first_gen, low_income, legacy, recruited_athlete, faculty_staff_child, rural, veteran, questbridge_finalist

  -- extracurriculars (tiers assigned in ETL with the same rubric Node 1 applies to live applicants)
  ec_tier_summary        jsonb not null default '{}'::jsonb,
  -- {"tier1":0,"tier2":2,"tier3":4,"tier4":3,"ec_score":6.25,"tier_derived_ec_rating":1.76}
  activities             jsonb not null default '[]'::jsonb,
  -- [{"description":"USACO Platinum; ...","role":"Founder","tier":2,"tier_rationale":"..."}]
  awards                 jsonb not null default '[]'::jsonb,   -- [{"name":"AIME qualifier","level":"national"}]
  spike_summary          text,
  essay_notes            text,
  lor_notes              text,
  headline               text,                                  -- "3.98 UW · 1560 SAT · 12 AP · CS · T1:0 T2:2"

  -- outcomes: canonical school slugs (FK-like; validated by the resolver, not by FK on arrays)
  accepted_schools       text[] not null default '{}',
  waitlisted_schools     text[] not null default '{}',
  rejected_schools       text[] not null default '{}',
  decisions_detail       jsonb not null default '[]'::jsonb,  -- [{"slug":"mit","outcome":"rejected","round":"EA","as_written":"MIT"}]
  applied_schools        text[] generated always as (accepted_schools || waitlisted_schools || rejected_schools) stored,
  committed_school       text,

  -- retrieval
  profile_text           text not null,                         -- deterministic canonical text (app/profile_text.py)
  embedding              extensions.vector(768),
  fts                    tsvector generated always as (to_tsvector('english', profile_text)) stored,

  -- extraction metadata
  extraction_confidence  text check (extraction_confidence in ('high','medium','low')),
  extraction_issues      text[] not null default '{}',
  extraction_model       text,
  created_at             timestamptz not null default now(),

  constraint outcome_arrays_disjoint check (
    not (accepted_schools && waitlisted_schools)
    and not (accepted_schools && rejected_schools)
    and not (waitlisted_schools && rejected_schools)
  ),
  constraint has_any_decision check (cardinality(accepted_schools || waitlisted_schools || rejected_schools) > 0)
);

comment on table public.applicant_twins is 'Self-reported Reddit applicant profiles with ground-truth outcomes; the retrieval corpus for Applicant Twins RAG.';

-- ANN index for unfiltered similarity (cohort explorer, cluster views)
create index applicant_twins_embedding_hnsw
  on public.applicant_twins using hnsw (embedding extensions.vector_cosine_ops)
  with (m = 16, ef_construction = 64);

-- Hybrid-search prefilter: "which twins applied to <school>" (array overlap/containment uses GIN)
create index applicant_twins_applied_gin  on public.applicant_twins using gin (applied_schools);
create index applicant_twins_accepted_gin on public.applicant_twins using gin (accepted_schools);
create index applicant_twins_hooks_gin    on public.applicant_twins using gin (hooks);
create index applicant_twins_fts_gin      on public.applicant_twins using gin (fts);
create index applicant_twins_major_idx    on public.applicant_twins (major_category, applicant_type);
create index applicant_twins_stats_idx    on public.applicant_twins (sat_score, gpa_uw);
create index applicant_twins_cycle_idx    on public.applicant_twins (cycle_year);
