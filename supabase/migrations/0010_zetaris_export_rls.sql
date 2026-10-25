-- Supabase turns on row-level security for new tables. With RLS on and no policy, zetaris_reader (a non-owner)
-- sees zero rows in zetaris_export, so the Zetaris JDBC datasource would see empty tables.
-- Read-only policies for the reader keep RLS on for every other role.
do $$
declare t text;
begin
  foreach t in array array['universities', 'twin_school_outcomes', 'school_major_stats'] loop
    execute format('drop policy if exists zetaris_reader_select on zetaris_export.%I', t);
    execute format('create policy zetaris_reader_select on zetaris_export.%I for select to zetaris_reader using (true)', t);
  end loop;
end $$;
