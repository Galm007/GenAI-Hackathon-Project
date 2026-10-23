-- Supabase installs extensions into the `extensions` schema; the default search_path includes it.
create extension if not exists vector   with schema extensions;   -- pgvector >= 0.8
create extension if not exists pg_trgm  with schema extensions;   -- fuzzy school-name matching
create extension if not exists pg_cron;                           -- TTL purge of evaluation runs

create type public.c7_level       as enum ('very_important', 'important', 'considered', 'not_considered');
create type public.test_policy    as enum ('required', 'optional', 'blind', 'flexible', 'unknown');
create type public.applicant_type as enum ('first_year', 'transfer');
create type public.school_control as enum ('public', 'private_nonprofit', 'private_forprofit');

-- Canonical C7 factor keys (CDS 2024-25 naming; racial/ethnic status was removed post-SFFA and is intentionally absent).
create or replace function public.c7_factor_keys()
returns text[]
language sql immutable parallel safe
as $$
  select array[
    'rigor', 'class_rank', 'academic_gpa', 'test_scores', 'essay', 'recommendations',
    'interview', 'extracurriculars', 'talent_ability', 'character', 'first_generation',
    'alumni_relation', 'geographic_residence', 'state_residency', 'religious_affiliation',
    'volunteer_work', 'work_experience', 'applicant_interest'
  ]::text[]
$$;

-- CHECK helper: every key is a known C7 factor and every value is a valid level.
create or replace function public.c7_is_valid(w jsonb)
returns boolean
language sql immutable parallel safe
as $$
  select jsonb_typeof(w) = 'object'
     and coalesce(bool_and(
           e.key = any (public.c7_factor_keys())
       and e.value #>> '{}' in ('very_important', 'important', 'considered', 'not_considered')
         ), true)
  from jsonb_each(w) as e
$$;

-- Canonical major buckets shared by ETL, grader and scoring (keep in sync with schemas/common.py::MajorCategory).
create or replace function public.major_category_keys()
returns text[]
language sql immutable parallel safe
as $$
  select array[
    'computer_science', 'computer_engineering', 'electrical_engineering', 'mechanical_aerospace',
    'other_engineering', 'math_stats', 'data_science', 'physics_astro', 'chemistry', 'biology',
    'neuroscience', 'pre_health', 'economics', 'business', 'political_science', 'psychology',
    'social_sciences_other', 'humanities', 'arts_design', 'architecture', 'undecided', 'other'
  ]::text[]
$$;
