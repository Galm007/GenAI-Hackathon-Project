create table public.universities_cds (
  -- identity
  slug                  text primary key check (slug ~ '^[a-z0-9_]+$'),   -- 'mit', 'uiuc', 'ut_austin'
  unitid                integer unique,                                     -- IPEDS id (= Scorecard id)
  name                  text not null,
  short_name            text,
  city                  text,
  state                 char(2),
  control               public.school_control,
  peer_group            text not null default 'other'
                        check (peer_group in ('hyps','t20_private','public_ivy','uc','t50_private',
                                              'lac_elite','tech','other')),
  website               text,

  -- selectivity (CDS C1 / C21; Scorecard fallback)
  applicants            integer check (applicants >= 0),
  admits                integer check (admits >= 0),
  enrolled              integer check (enrolled >= 0),
  admit_rate            numeric(5,4) check (admit_rate between 0 and 1),
  ed_applicants         integer,
  ed_admits             integer,
  ed_admit_rate         numeric(5,4) check (ed_admit_rate between 0 and 1),
  ea_admit_rate         numeric(5,4) check (ea_admit_rate between 0 and 1),
  rd_admit_rate         numeric(5,4) check (rd_admit_rate between 0 and 1),
  yield_rate            numeric(5,4) check (yield_rate between 0 and 1),
  in_state_admit_rate   numeric(5,4) check (in_state_admit_rate between 0 and 1),     -- publics, when published
  out_state_admit_rate  numeric(5,4) check (out_state_admit_rate between 0 and 1),

  -- testing (CDS C9; Scorecard fallback)
  test_policy           public.test_policy not null default 'unknown',
  sat_composite_25      smallint check (sat_composite_25 between 400 and 1600),
  sat_composite_50      smallint check (sat_composite_50 between 400 and 1600),
  sat_composite_75      smallint check (sat_composite_75 between 400 and 1600),
  sat_ebrw_25           smallint check (sat_ebrw_25 between 200 and 800),
  sat_ebrw_75           smallint check (sat_ebrw_75 between 200 and 800),
  sat_math_25           smallint check (sat_math_25 between 200 and 800),
  sat_math_75           smallint check (sat_math_75 between 200 and 800),
  act_composite_25      smallint check (act_composite_25 between 1 and 36),
  act_composite_75      smallint check (act_composite_75 between 1 and 36),
  pct_submitting_sat    numeric(5,4),
  pct_submitting_act    numeric(5,4),

  -- high school record (CDS C10-C12)
  avg_hs_gpa            numeric(3,2),
  gpa_distribution      jsonb not null default '[]'::jsonb,   -- [{"bucket":"4.0","pct":0.63}, ...]
  pct_top10_class       numeric(5,4),

  -- CDS C7: {"rigor":"very_important","essay":"important","applicant_interest":"not_considered", ...}
  c7_weights            jsonb not null default '{}'::jsonb
                        constraint c7_weights_valid check (public.c7_is_valid(c7_weights)),

  -- CDS C21/C22: {"ed":true,"ed2":false,"ea":false,"rea":false}
  early_plans           jsonb not null default '{}'::jsonb,

  -- CDS Section D: {"accepts_transfers":true,"applicants":3120,"admits":180,"enrolled":120,"min_college_gpa":null}
  transfer_profile      jsonb not null default '{}'::jsonb,

  -- per-major competitiveness, keyed by major_category:
  -- {"computer_science":{"multiplier":0.38,"direct_admit":true,"college":"Grainger College of Engineering",
  --                      "source":"override","source_url":"https://...","n":212}}
  major_competitiveness jsonb not null default '{}'::jsonb,

  strategic_priorities  text[] not null default '{}',
  institutional_notes   text,
  cds_year              text,                                   -- '2024-2025'
  source_urls           jsonb not null default '{}'::jsonb,     -- {"cds":"...","scorecard":"..."}
  data_quality          jsonb not null default '{}'::jsonb,     -- {"imputed":["sat_composite_25"],"c7_source":"cds"}
  updated_at            timestamptz not null default now()
);

comment on table  public.universities_cds is 'One row per institution: Scorecard + Common Data Set facts, C7 weights, major multipliers.';
comment on column public.universities_cds.c7_weights is 'CDS C7 relative importance of 18 admission factors. Keys from c7_factor_keys().';

create index universities_cds_peer_idx on public.universities_cds (peer_group);
create index universities_cds_admit_idx on public.universities_cds (admit_rate);

-- Reddit names schools in hundreds of ways ("UMich", "Michigan", "UM Ann Arbor"); the resolver maps them here.
create table public.school_aliases (
  alias  text primary key check (alias = lower(alias)),
  slug   text not null references public.universities_cds (slug) on delete cascade
);
create index school_aliases_trgm_idx on public.school_aliases using gin (alias extensions.gin_trgm_ops);
create index school_aliases_slug_idx on public.school_aliases (slug);

create or replace function public.touch_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at := now();
  return new;
end $$;

create trigger universities_cds_touch
before update on public.universities_cds
for each row execute function public.touch_updated_at();
