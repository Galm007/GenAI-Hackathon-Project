-- zetaris/sql/04_security.sql: least privilege for the agents --------------------------------------
ADD USER WITH (
  email '${ZETARIS_AGENT_EMAIL}',
  name 'adcom_agent',
  level 'general',
  password '${ZETARIS_AGENT_PASSWORD}'
);
CREATE ROLE 'adcom_agent_role' DESCRIBE BY "AdCom agents, read-only semantic layer";
ASSIGN USER '${ZETARIS_AGENT_EMAIL}' TO ROLE 'adcom_agent_role';
GRANT SELECT ON VIEW TABLE ADCOM.v_school_profile TO ROLE 'adcom_agent_role';
GRANT SELECT ON VIEW TABLE ADCOM.v_school_c7_long TO ROLE 'adcom_agent_role';
GRANT SELECT ON VIEW TABLE ADCOM.v_major_stats TO ROLE 'adcom_agent_role';
GRANT SELECT ON VIEW TABLE ADCOM.v_reddit_calibration TO ROLE 'adcom_agent_role';
GRANT SELECT ON VIEW TABLE ADCOM.v_admitted_medians TO ROLE 'adcom_agent_role';
GRANT SELECT ON VIEW TABLE ADCOM.v_peer_benchmarks TO ROLE 'adcom_agent_role';
GRANT SELECT ON DATALAKE TABLE ADCOM_LAKE.gold.school_profile TO ROLE 'adcom_agent_role';
-- Confirmed against the running stack: role and user names are quoted, the user is assigned by email, and an
-- object-type keyword follows ON. The agent password must have a lowercase letter, an uppercase letter, a digit and
-- one of $@!%*? &, at least 8 characters. Views are granted one by one, never as a namespace: v_ipeds_c7 stays internal.
