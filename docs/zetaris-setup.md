# Zetaris setup (Track A)

Steps only. No secrets in this file; the bundle's `.env` and every password stay out of git (`zetaris-platform/` is in `.gitignore`). Plan reference: `MASTER_PLAN.md` §2.10.2 and §2.10.4.

## 1. Bring up the bundle

> The Reddit extraction run pauses this stack automatically (`etl/resources.py`, `docker compose stop` then `start`) so the local Gemma model has RAM. Give it about a minute to become healthy afterwards; re-run `./verify.sh` if in doubt.

1. Give Docker 8 GB of memory and 4 CPUs. On a 16 GB laptop set `ZSPARK_DRIVER_MEM=4g` and `ZSPARK_DRIVER_CORES=4` in `zetaris-platform/.env` before the first start.
2. `docker login zetarishackathon.azurecr.io` (the command from the Zetaris Cloud download page).
3. From `zetaris-platform/`: `./preflight.sh`, `docker compose pull`, `docker compose up -d`. The first start takes 5-10 minutes.
4. `./verify.sh` should print nine PASS lines.
5. In `zetaris-platform/conf/spark-defaults.conf` set `spark.sql.shuffle.partitions 4`, then `docker compose restart driver`.
6. Sign in at http://localhost:3000 and change the admin password.
7. Never run `docker compose down -v` here: it destroys the metastore and the encryption keypair.

## 2. Prerequisites for the SQL files

- Migrations 0001-0009 applied to Supabase (A01-A04). `0009` creates `zetaris_export` and the `zetaris_reader` role.
- Set a password for `zetaris_reader` out of band (`alter role zetaris_reader password '...'`), never in a migration.
- Download the federal files once into `data/public/` (git-ignored):
  - `data/public/scorecard/`: College Scorecard "Most Recent Institution-Level Data" CSV.
  - `data/public/ipeds_adm/`: IPEDS `ADMyyyy.csv`.
- Copy them into the driver's shared volume:
  ```
  docker compose cp data/public/scorecard/. driver:/home/zetaris/customer-data/shared/adcom/scorecard/
  docker compose cp data/public/ipeds_adm/. driver:/home/zetaris/customer-data/shared/adcom/ipeds_adm/
  ```
- Environment variables read by the SQL files (`${VAR}` placeholders): `SUPABASE_POOLER_HOST` (the session pooler, not the IPv6-only direct host), `ZETARIS_PG_USER` (`zetaris_reader.<project-ref>`), `ZETARIS_PG_PASSWORD`, `ZETARIS_AGENT_EMAIL`, `ZETARIS_AGENT_PASSWORD`.

## 3. Apply the SQL

Apply `zetaris/sql/` in order, with `run_etl zetaris-setup` (step A14) or by pasting each file into the Zetaris UI's SQL editor with the placeholders filled in. Create the lake folder first: `docker compose exec driver mkdir -p /home/zetaris/customer-data/shared/adcom/lake`.

1. `01_sources.sql`: Supabase datasource (with `schema "zetaris_export"`), public-file filestore tables, Iceberg lake.
2. `02_views.sql`: the `ADCOM` semantic layer.
3. `03_gold.sql`: `gold.school_profile`. The `INSERT OVERWRITE` line is the refresh statement and is run after each data refresh.
4. `04_security.sql`: `adcom_agent` user and role. The agent password needs a lowercase letter, an uppercase letter, a digit and one of `$@!%*?&`.

Programmatic DDL goes to `POST /api/proxy/sql-editor/sqls/run` (the query route used by `app/zetaris.py` accepts only `SELECT`).

## 4. Check

- `SELECT * FROM ADCOM.v_school_profile WHERE slug = 'uiuc'` returns a row.
- Signed in as `adcom_agent`, `SELECT * FROM ADCOM_PG.universities` is denied, and so are `ADCOM.v_ipeds_c7` and `ADCOM_PUBLIC.*`.
- `./verify.sh` shows nine PASS lines.

## Supabase side (once)

- Migrations 0009 and 0010 (0010 adds the read policies the reader needs: RLS is on by default).
- `zetaris_reader` password set; the datasource connects through the **session** pooler.

Everything that was marked "(verify at Hour 1)" is now confirmed (see D-031).
