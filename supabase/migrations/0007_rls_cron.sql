-- Browser (anon) may read public school facts; everything else is backend-only (service role bypasses RLS).
alter table public.universities_cds   enable row level security;
alter table public.school_aliases     enable row level security;
alter table public.applicant_twins    enable row level security;   -- no policies → anon/authenticated get nothing
alter table public.evaluation_runs    enable row level security;
alter table public.web_research_cache enable row level security;

create policy "anon read universities" on public.universities_cds for select to anon, authenticated using (true);
create policy "anon read aliases"      on public.school_aliases   for select to anon, authenticated using (true);

-- Materialized views can't have RLS: revoke direct API access.
revoke all on public.twin_school_outcomes from anon, authenticated;
revoke all on public.school_major_stats   from anon, authenticated;
revoke all on public.school_reddit_calibration from anon, authenticated;

-- RPCs that touch twins are backend-only.
revoke execute on function public.match_applicant_twins      from anon, authenticated, public;
revoke execute on function public.twin_neighborhood_stats    from anon, authenticated, public;
revoke execute on function public.major_arbitrage_candidates from anon, authenticated, public;
revoke execute on function public.refresh_twin_stats()       from anon, authenticated, public;
grant  execute on function public.resolve_school(text, int)  to anon, authenticated;

-- Privacy: purge evaluation runs after 24h; prune stale research cache weekly.
select cron.schedule('purge-evaluation-runs', '*/30 * * * *',
  $$delete from public.evaluation_runs where expires_at < now()$$);
select cron.schedule('prune-research-cache', '0 4 * * 0',
  $$delete from public.web_research_cache where fetched_at < now() - interval '14 days'$$);
