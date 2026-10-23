-- One row per (twin, school decision)
create materialized view public.twin_school_outcomes as
select t.id as twin_id, t.applicant_type, t.major_category, t.cycle_year, d.slug, d.outcome
from public.applicant_twins t
cross join lateral (
  select unnest(t.accepted_schools)   as slug, 'accepted'::text   as outcome
  union all
  select unnest(t.waitlisted_schools),          'waitlisted'::text
  union all
  select unnest(t.rejected_schools),            'rejected'::text
) d;

create unique index twin_school_outcomes_pk on public.twin_school_outcomes (twin_id, slug);
create index twin_school_outcomes_slug_idx on public.twin_school_outcomes (slug, major_category);

-- Per (school, major) admit rate among Reddit applicants, with a Bayesian-smoothed multiplier
-- relative to that school's overall Reddit admit rate (prior strength = 20 pseudo-applicants).
create materialized view public.school_major_stats as
with school_tot as (
  select slug,
         count(*)::int                                     as n_all,
         avg((outcome = 'accepted')::int)::double precision as rate_all
  from public.twin_school_outcomes
  where applicant_type = 'first_year'
  group by slug
)
select o.slug,
       o.major_category,
       count(*)::int                                            as n,
       count(*) filter (where o.outcome = 'accepted')::int      as n_accepted,
       count(*) filter (where o.outcome = 'waitlisted')::int    as n_waitlisted,
       count(*) filter (where o.outcome = 'rejected')::int      as n_rejected,
       avg((o.outcome = 'accepted')::int)::double precision     as reddit_admit_rate,
       st.rate_all                                              as school_reddit_admit_rate,
       st.n_all                                                 as school_n,
       case when st.rate_all > 0 then
         ((count(*) filter (where o.outcome = 'accepted') + 20.0 * st.rate_all) / (count(*) + 20.0)) / st.rate_all
       else 1.0 end                                             as smoothed_multiplier
from public.twin_school_outcomes o
join school_tot st using (slug)
where o.applicant_type = 'first_year'
group by o.slug, o.major_category, st.rate_all, st.n_all;

create unique index school_major_stats_pk on public.school_major_stats (slug, major_category);

-- Self-selection calibration: how much higher is the Reddit admit rate than the official one?
-- odds_inflation = odds(reddit) / odds(official), clamped to [1, 8]. Node 3 divides twin odds by this.
create view public.school_reddit_calibration
with (security_invoker = true) as
select u.slug,
       u.admit_rate::double precision as official_admit_rate,
       st.n_all                       as reddit_n,
       st.rate_all                    as reddit_admit_rate,
       case
         when u.admit_rate > 0 and u.admit_rate < 1 and st.rate_all > 0 and st.rate_all < 1 then
           least(8.0, greatest(1.0,
             (st.rate_all / (1 - st.rate_all)) / (u.admit_rate::double precision / (1 - u.admit_rate::double precision))))
         else 1.0
       end                            as odds_inflation
from public.universities_cds u
join (
  select slug, count(*)::int as n_all, avg((outcome = 'accepted')::int)::double precision as rate_all
  from public.twin_school_outcomes
  where applicant_type = 'first_year'
  group by slug
) st using (slug);

-- Called by etl/refresh_stats.py after each load.
create or replace function public.refresh_twin_stats()
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  refresh materialized view concurrently public.twin_school_outcomes;
  refresh materialized view concurrently public.school_major_stats;
end $$;
