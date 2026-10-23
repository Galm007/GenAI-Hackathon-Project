create or replace function public.admitted_profile_medians(target_school text)
returns table (n int, gpa_uw double precision, sat double precision, advanced double precision,
               ec_rating double precision, spike_points double precision)
language sql
stable
set search_path = public, extensions
as $$
  select count(*)::int,
         percentile_cont(0.5) within group (order by t.gpa_uw),
         percentile_cont(0.5) within group (order by t.sat_score),
         percentile_cont(0.5) within group (order by coalesce(t.ap_count, 0) + coalesce(t.dual_enrollment_count, 0)),
         percentile_cont(0.5) within group (order by (t.ec_tier_summary ->> 'tier_derived_ec_rating')::double precision),
         percentile_cont(0.5) within group (order by 2 * coalesce((t.ec_tier_summary ->> 'tier1')::int, 0)
                                                     + coalesce((t.ec_tier_summary ->> 'tier2')::int, 0))
  from public.applicant_twins t
  where t.accepted_schools @> array[target_school]
    and t.applicant_type = 'first_year'
$$;

revoke execute on function public.admitted_profile_medians(text) from anon, authenticated, public;
