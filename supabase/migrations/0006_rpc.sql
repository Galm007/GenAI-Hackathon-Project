create or replace function public.match_applicant_twins(
  query_embedding  extensions.vector(1536),
  target_schools   text[],                                  -- usually one slug; peer fallback passes several
  match_count      int                    default 5,
  applicant_kind   public.applicant_type  default 'first_year',
  major_filter     text                   default null,     -- exact major_category, or null for all
  query_gpa_uw     numeric                default null,
  query_sat        int                    default null,
  outcome_filter   text                   default 'any',    -- 'any' | 'accepted' | 'waitlisted' | 'rejected'
  min_cycle_year   int                    default 2019,
  semantic_weight  double precision       default 0.70
)
returns table (
  id                   uuid,
  reddit_id            text,
  source_url           text,
  cycle_year           smallint,
  matched_school       text,
  outcome              text,
  gpa_uw               numeric,
  gpa_w                numeric,
  sat_score            smallint,
  act_score            smallint,
  ap_count             smallint,
  intended_major       text,
  major_category       text,
  hooks                text[],
  ec_tier_summary      jsonb,
  activities           jsonb,
  awards               jsonb,
  spike_summary        text,
  headline             text,
  semantic_similarity  double precision,
  stat_proximity       double precision,
  hybrid_score         double precision
)
language sql
stable
parallel safe
set search_path = public, extensions
as $$
  with candidates as materialized (
    -- 1) SQL prefilter via GIN(applied_schools): only twins who applied to a target school
    select t.id, t.reddit_id, t.source_url, t.cycle_year, t.gpa_uw, t.gpa_w, t.sat_score, t.act_score,
           t.ap_count, t.intended_major, t.major_category, t.hooks, t.ec_tier_summary, t.activities,
           t.awards, t.spike_summary, t.headline, t.embedding,
           m.matched_school, m.outcome
    from public.applicant_twins t
    cross join lateral (
      -- outcome at the FIRST target school (in caller's priority order) this twin applied to
      select u.s as matched_school,
             case
               when u.s = any (t.accepted_schools)   then 'accepted'
               when u.s = any (t.waitlisted_schools) then 'waitlisted'
               else 'rejected'
             end as outcome
      from unnest(target_schools) with ordinality as u(s, ord)
      where u.s = any (t.applied_schools)
      order by u.ord
      limit 1
    ) m
    where t.applied_schools && target_schools
      and t.applicant_type = applicant_kind
      and t.embedding is not null
      and (major_filter is null or t.major_category = major_filter)
      and (t.cycle_year is null or t.cycle_year >= min_cycle_year)
  ),
  scored as (
    -- 2) exact cosine similarity + 3) structured stat kernels (missing stat → neutral 0.5)
    select c.*,
           1 - (c.embedding <=> query_embedding) as sem,
           0.5 * coalesce(exp(-power((c.gpa_uw - query_gpa_uw) / 0.08, 2)), 0.5)
         + 0.5 * coalesce(exp(-power((c.sat_score - query_sat) / 40.0, 2)), 0.5) as stat
    from candidates c
    where outcome_filter = 'any' or c.outcome = outcome_filter
  ),
  ranked as (
    select s.*, semantic_weight * s.sem + (1 - semantic_weight) * s.stat as hybrid
    from scored s
  )
  select r.id, r.reddit_id, r.source_url, r.cycle_year, r.matched_school, r.outcome,
         r.gpa_uw, r.gpa_w, r.sat_score, r.act_score, r.ap_count, r.intended_major, r.major_category,
         r.hooks, r.ec_tier_summary, r.activities, r.awards, r.spike_summary, r.headline,
         r.sem, r.stat, r.hybrid
  from ranked r
  order by r.hybrid desc
  limit match_count
$$;

create or replace function public.twin_neighborhood_stats(
  query_embedding  extensions.vector(1536),
  target_schools   text[],
  k                int                   default 50,
  applicant_kind   public.applicant_type default 'first_year',
  major_filter     text                  default null,
  query_gpa_uw     numeric               default null,
  query_sat        int                   default null
)
returns table (
  n                    int,
  n_accepted           int,
  n_waitlisted         int,
  n_rejected           int,
  sum_w                double precision,
  sum_w2               double precision,
  sum_w_admit          double precision,
  weighted_admit_rate  double precision,
  mean_similarity      double precision
)
language sql
stable
set search_path = public, extensions
as $$
  with nn as (
    select m.outcome,
           exp(10.0 * (m.hybrid_score - 1.0)) as w,
           m.semantic_similarity
    from public.match_applicant_twins(
           query_embedding => query_embedding,
           target_schools  => target_schools,
           match_count     => k,
           applicant_kind  => applicant_kind,
           major_filter    => major_filter,
           query_gpa_uw    => query_gpa_uw,
           query_sat       => query_sat
         ) m
  )
  select count(*)::int,
         count(*) filter (where nn.outcome = 'accepted')::int,
         count(*) filter (where nn.outcome = 'waitlisted')::int,
         count(*) filter (where nn.outcome = 'rejected')::int,
         coalesce(sum(nn.w), 0),
         coalesce(sum(nn.w * nn.w), 0),
         coalesce(sum(nn.w * (nn.outcome = 'accepted')::int), 0),
         sum(nn.w * (nn.outcome = 'accepted')::int) / nullif(sum(nn.w), 0),
         avg(nn.semantic_similarity)
  from nn
$$;

create or replace function public.major_arbitrage_candidates(
  query_embedding  extensions.vector(1536),
  target_school    text,
  query_gpa_uw     numeric default null,
  query_sat        int     default null,
  k                int     default 300,
  min_n            int     default 8
)
returns table (
  major_category              text,
  n_neighbors                 int,
  neighbor_admit_rate         double precision,
  school_n                    int,
  school_smoothed_multiplier  double precision
)
language sql
stable
set search_path = public, extensions
as $$
  with nn as (
    -- semantic_weight 0.30 → neighbors chosen mostly by academic stats, so many majors are represented
    select m.major_category, m.outcome
    from public.match_applicant_twins(
           query_embedding => query_embedding,
           target_schools  => array[target_school],
           match_count     => k,
           query_gpa_uw    => query_gpa_uw,
           query_sat       => query_sat,
           semantic_weight => 0.30
         ) m
  )
  select nn.major_category,
         count(*)::int,
         avg((nn.outcome = 'accepted')::int)::double precision,
         coalesce(sms.n, 0)::int,
         coalesce(sms.smoothed_multiplier, 1.0)
  from nn
  left join public.school_major_stats sms
         on sms.slug = target_school and sms.major_category = nn.major_category
  group by nn.major_category, sms.n, sms.smoothed_multiplier
  having count(*) >= min_n
  order by 3 desc
$$;

create or replace function public.resolve_school(q text, max_results int default 5)
returns table (slug text, name text, score real)
language sql
stable
set search_path = public, extensions
as $$
  select a.slug, u.name, max(similarity(a.alias, lower(q))) as score
  from public.school_aliases a
  join public.universities_cds u on u.slug = a.slug
  where a.alias % lower(q)
  group by a.slug, u.name
  order by 3 desc
  limit max_results
$$;
