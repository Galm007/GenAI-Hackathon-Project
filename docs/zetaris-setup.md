# Zetaris setup (Track A)

Steps only. No secrets in this file; the bundle's `.env` and every password stay out of git (`zetaris-platform/` is in `.gitignore`). Plan reference: `MASTER_PLAN.md` §2.10.2 and §2.10.4.

## 1. Bring up the bundle

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

Apply `zetaris/sql/` in order, either with `run_etl zetaris-setup` (step A14) or by pasting each file into the Zetaris UI's SQL editor with the placeholders filled in:

1. `01_sources.sql`: Supabase datasource, public-file filestore tables, Iceberg lake.
2. `02_views.sql`: the `ADCOM` semantic layer.
3. `03_gold.sql`: `gold.school_profile`. The `INSERT OVERWRITE` line is the refresh statement and is run after each data refresh.
4. `04_security.sql`: `adcom_agent` user and role.

## 4. Check

- `SELECT * FROM ADCOM.v_school_profile WHERE slug = 'uiuc'` returns a row.
- Signed in as `adcom_agent`, `SELECT * FROM ADCOM_PG.universities` is denied.
- `SHOW ROLE ASSIGNED TO USER` lists `adcom_agent_role` for the agent.

## Open "(verify at Hour 1)" items

Still marked in the SQL files and the plan until each is confirmed against a stack that has the data loaded:

- Local-path syntax for the filestore tables (`file:///...`) in `01_sources.sql`.
- The ADMCON column list for your IPEDS file year in `02_views.sql`.
- The `GRANT` principal form and whether `ASSIGN USER` takes the email or the name in `04_security.sql`.
