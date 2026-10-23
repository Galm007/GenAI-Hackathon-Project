create schema if not exists zetaris_export;

-- Read-only login role for the Zetaris JDBC datasource (password set out of band, never committed).
do $$ begin
  if not exists (select 1 from pg_roles where rolname = 'zetaris_reader') then
    create role zetaris_reader login;
  end if;
end $$;
grant usage on schema zetaris_export to zetaris_reader;
alter default privileges in schema zetaris_export grant select on tables to zetaris_reader;

create table if not exists zetaris_export.universities (
  slug text primary key, unitid integer, name text, peer_group text, control text, state text,
  admit_rate double precision, ed_admit_rate double precision, ea_admit_rate double precision,
  rd_admit_rate double precision, in_state_admit_rate double precision, out_state_admit_rate double precision,
  test_policy text, sat_composite_25 integer, sat_composite_75 integer, act_composite_25 integer,
  act_composite_75 integer, cds_year text,
  c7_weights text, early_plans text, major_competitiveness text, transfer_profile text   -- JSON as text
);

create table if not exists zetaris_export.twin_school_outcomes (
  twin_id uuid, slug text, outcome text, applicant_type text, major_category text, cycle_year integer,
  gpa_uw double precision, sat_score integer, ap_count integer, advanced_courses integer,
  tier1 integer, tier2 integer, tier_derived_ec_rating double precision, hooks text,  -- comma-joined
  primary key (twin_id, slug)
);

create table if not exists zetaris_export.school_major_stats (
  slug text, major_category text, n integer, n_accepted integer, n_waitlisted integer, n_rejected integer,
  reddit_admit_rate double precision, school_reddit_admit_rate double precision, smoothed_multiplier double precision,
  primary key (slug, major_category)
);

grant select on all tables in schema zetaris_export to zetaris_reader;

-- Extends 0004's refresh: rebuild the export tables in the same transaction as the MVs.
create or replace function public.refresh_twin_stats()
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  refresh materialized view concurrently public.twin_school_outcomes;
  refresh materialized view concurrently public.school_major_stats;

  truncate zetaris_export.universities, zetaris_export.twin_school_outcomes, zetaris_export.school_major_stats;

  insert into zetaris_export.universities
  select slug, unitid, name, peer_group, control::text, state, admit_rate, ed_admit_rate, ea_admit_rate,
         rd_admit_rate, in_state_admit_rate, out_state_admit_rate, test_policy::text, sat_composite_25,
         sat_composite_75, act_composite_25, act_composite_75, cds_year,
         c7_weights::text, early_plans::text, major_competitiveness::text, transfer_profile::text
  from public.universities_cds;

  insert into zetaris_export.twin_school_outcomes
  select o.twin_id, o.slug, o.outcome, o.applicant_type::text, o.major_category, o.cycle_year,
         t.gpa_uw, t.sat_score, t.ap_count, coalesce(t.ap_count, 0) + coalesce(t.dual_enrollment_count, 0),
         coalesce((t.ec_tier_summary ->> 'tier1')::int, 0), coalesce((t.ec_tier_summary ->> 'tier2')::int, 0),
         (t.ec_tier_summary ->> 'tier_derived_ec_rating')::double precision, array_to_string(t.hooks, ',')
  from public.twin_school_outcomes o
  join public.applicant_twins t on t.id = o.twin_id;

  insert into zetaris_export.school_major_stats
  select slug, major_category, n, n_accepted, n_waitlisted, n_rejected, reddit_admit_rate,
         school_reddit_admit_rate, smoothed_multiplier
  from public.school_major_stats;
end $$;
