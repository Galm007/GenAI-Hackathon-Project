-- zetaris/sql/01_sources.sql ------------------------------------------------------------------
-- (a) Supabase, federated over JDBC (Postgres driver 42.7 ships in the Zetaris driver image)
CREATE DATASOURCE ADCOM_PG DESCRIBE BY "AdCom Supabase export schema" OPTIONS (
  jdbcdriver "org.postgresql.Driver",
  jdbcurl "jdbc:postgresql://${SUPABASE_POOLER_HOST}:5432/postgres?sslmode=require",
  username "${ZETARIS_PG_USER}",
  password "${ZETARIS_PG_PASSWORD}",
  schema "zetaris_export"
);
REGISTER DATASOURCE TABLES FROM ADCOM_PG;

-- (b) Federal files, read in place. Copy them into the driver's shared volume first:
--   docker compose cp data/public/scorecard/. driver:/home/zetaris/customer-data/shared/adcom/scorecard/
--   docker compose cp data/public/ipeds_adm/. driver:/home/zetaris/customer-data/shared/adcom/ipeds_adm/
-- Confirmed: file:/// paths work. The `schema` option is what selects zetaris_export (the pooler ignores
-- currentSchema and role-level search_path); without it, REGISTER lists the public tables instead.
CREATE LIGHTNING DATABASE ADCOM_PUBLIC DESCRIBE BY "College Scorecard and IPEDS public files" OPTIONS ();

CREATE LIGHTNING FILESTORE TABLE scorecard_institutions FROM ADCOM_PUBLIC
FORMAT csv
OPTIONS (
  path "file:///home/zetaris/customer-data/shared/adcom/scorecard",
  header "true",
  inferSchema "false"
);

CREATE LIGHTNING FILESTORE TABLE ipeds_adm FROM ADCOM_PUBLIC
FORMAT csv
OPTIONS (
  path "file:///home/zetaris/customer-data/shared/adcom/ipeds_adm",
  header "true",
  inferSchema "false"
);

-- (c) Local Iceberg lakehouse for the gold tables on the hot path. Create the folder first:
--   docker compose exec driver mkdir -p /home/zetaris/customer-data/shared/adcom/lake
CREATE DATALAKE ADCOM_LAKE OPTIONS (
  storageType 'Local',
  storagePath '/home/zetaris/customer-data/shared/adcom/lake'
);
