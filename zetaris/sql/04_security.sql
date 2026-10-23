-- zetaris/sql/04_security.sql: least privilege for the agents --------------------------------------
ADD USER WITH (
  email '${ZETARIS_AGENT_EMAIL}',
  name 'adcom_agent',
  level 'general',
  password '${ZETARIS_AGENT_PASSWORD}'
);
CREATE ROLE adcom_agent_role DESCRIBE BY "AdCom agents: read-only semantic layer";
ASSIGN USER ${ZETARIS_AGENT_EMAIL} TO ROLE adcom_agent_role;
GRANT SELECT ON ADCOM.v_school_profile     TO ROLE adcom_agent_role;
GRANT SELECT ON ADCOM.v_school_c7_long     TO ROLE adcom_agent_role;
GRANT SELECT ON ADCOM.v_major_stats        TO ROLE adcom_agent_role;
GRANT SELECT ON ADCOM.v_reddit_calibration TO ROLE adcom_agent_role;
GRANT SELECT ON ADCOM.v_admitted_medians   TO ROLE adcom_agent_role;
GRANT SELECT ON ADCOM.v_peer_benchmarks    TO ROLE adcom_agent_role;
GRANT SELECT ON ADCOM_LAKE.gold.school_profile TO ROLE adcom_agent_role;
-- (verify at Hour 1) principal_spec form ("ROLE x" vs "x") and whether ASSIGN USER takes the email or the
-- name. SHOW ROLE ASSIGNED TO USER confirms it. The agent never sees ADCOM_PG or the raw files directly.
