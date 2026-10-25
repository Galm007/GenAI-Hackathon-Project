-- zetaris/sql/02_views.sql: the semantic layer the agents query ---------------------------------
CREATE SCHEMASTORE CONTAINER ADCOM;

-- IPEDS admission considerations → coarse C7-style levels for schools without a parsed CDS.
-- IPEDS codes: 1 required, 2 recommended, 3 neither required nor recommended, 5 considered but not required.
-- ADMCON1..ADMCON12 confirmed present in ADM2023 (the 2023-24 file); check the data dictionary if you load another year.
CREATE SCHEMASTORE VIEW v_ipeds_c7 WITH CONTAINER ADCOM AS (
  SELECT TRY_CAST(UNITID AS INT) AS unitid,
         to_json(named_struct(
           'academic_gpa',    CASE ADMCON1 WHEN '1' THEN 'important' WHEN '2' THEN 'considered' WHEN '5' THEN 'considered' ELSE 'not_considered' END,
           'class_rank',      CASE ADMCON2 WHEN '1' THEN 'important' WHEN '2' THEN 'considered' WHEN '5' THEN 'considered' ELSE 'not_considered' END,
           'rigor',           CASE ADMCON3 WHEN '1' THEN 'important' WHEN '2' THEN 'considered' WHEN '5' THEN 'considered' ELSE 'not_considered' END,
           'recommendations', CASE ADMCON5 WHEN '1' THEN 'important' WHEN '2' THEN 'considered' WHEN '5' THEN 'considered' ELSE 'not_considered' END,
           'test_scores',     CASE ADMCON7 WHEN '1' THEN 'important' WHEN '2' THEN 'considered' WHEN '5' THEN 'considered' ELSE 'not_considered' END
         )) AS c7_json,
         TRY_CAST(APPLCN AS DOUBLE) AS applicants, TRY_CAST(ADMSSN AS DOUBLE) AS admits,
         TRY_CAST(SATVR25 AS INT) + TRY_CAST(SATMT25 AS INT) AS sat_25,
         TRY_CAST(SATVR75 AS INT) + TRY_CAST(SATMT75 AS INT) AS sat_75
  FROM ADCOM_PUBLIC.ipeds_adm
);

CREATE SCHEMASTORE VIEW v_school_profile WITH CONTAINER ADCOM AS (
  SELECT
    u.slug, u.unitid,
    COALESCE(u.name, sc.INSTNM)                                             AS name,
    sc.CITY                                                                 AS city,
    COALESCE(u.state, sc.STABBR)                                            AS state,
    COALESCE(u.control, CASE sc.CONTROL WHEN '1' THEN 'public' WHEN '2' THEN 'private_nonprofit'
                                         WHEN '3' THEN 'private_forprofit' END) AS control,
    u.peer_group,
    COALESCE(u.admit_rate, TRY_CAST(sc.ADM_RATE AS DOUBLE), ip.admits / NULLIF(ip.applicants, 0)) AS admit_rate,
    CASE WHEN u.admit_rate IS NOT NULL AND u.cds_year IS NOT NULL THEN 'cds'
         WHEN u.admit_rate IS NOT NULL THEN 'scorecard'
         WHEN sc.ADM_RATE IS NOT NULL AND sc.ADM_RATE NOT IN ('NULL', 'PrivacySuppressed') THEN 'scorecard'
         ELSE 'ipeds' END                                                   AS admit_rate_source,
    u.ed_admit_rate, u.ea_admit_rate, u.rd_admit_rate, u.in_state_admit_rate, u.out_state_admit_rate,
    COALESCE(u.sat_composite_25, TRY_CAST(sc.SATVR25 AS INT) + TRY_CAST(sc.SATMT25 AS INT), ip.sat_25) AS sat_composite_25,
    COALESCE(u.sat_composite_75, TRY_CAST(sc.SATVR75 AS INT) + TRY_CAST(sc.SATMT75 AS INT), ip.sat_75) AS sat_composite_75,
    COALESCE(u.act_composite_25, TRY_CAST(sc.ACTCM25 AS INT))               AS act_composite_25,
    COALESCE(u.act_composite_75, TRY_CAST(sc.ACTCM75 AS INT))               AS act_composite_75,
    COALESCE(NULLIF(u.test_policy, 'unknown'),
             CASE sc.ADMCON7 WHEN '1' THEN 'required' WHEN '2' THEN 'optional' WHEN '5' THEN 'optional'
                             WHEN '3' THEN 'blind' END, 'unknown')          AS test_policy,
    CASE WHEN u.c7_weights IS NOT NULL AND u.c7_weights <> '{}' THEN u.c7_weights ELSE ip.c7_json END AS c7_weights,
    CASE WHEN u.c7_weights IS NOT NULL AND u.c7_weights <> '{}' THEN 'cds' ELSE 'ipeds' END AS c7_source,
    u.early_plans, u.major_competitiveness, u.transfer_profile, u.cds_year,
    TRY_CAST(sc.UGDS AS INT)                                                AS undergrad_enrollment
  FROM ADCOM_PG.universities u
  LEFT JOIN ADCOM_PUBLIC.scorecard_institutions sc ON TRY_CAST(sc.UNITID AS INT) = u.unitid
  LEFT JOIN ADCOM.v_ipeds_c7 ip ON ip.unitid = u.unitid
);

-- One row per (school, factor): the easiest shape for the agent's SQL tool
CREATE SCHEMASTORE VIEW v_school_c7_long WITH CONTAINER ADCOM AS (
  SELECT p.slug, p.name, p.c7_source, f.factor, f.level
  FROM ADCOM.v_school_profile p
  LATERAL VIEW explode(from_json(p.c7_weights, 'map<string,string>')) f AS factor, level
);

CREATE SCHEMASTORE VIEW v_major_stats WITH CONTAINER ADCOM AS (
  SELECT m.slug, m.major_category, m.n, m.n_accepted, m.n_waitlisted, m.n_rejected,
         m.reddit_admit_rate, m.school_reddit_admit_rate, m.smoothed_multiplier
  FROM ADCOM_PG.school_major_stats m
);

-- Reddit self-selection: odds(reddit) / odds(official), clamped to [1, 8] (same rule as §2.5)
CREATE SCHEMASTORE VIEW v_reddit_calibration WITH CONTAINER ADCOM AS (
  SELECT p.slug, p.admit_rate AS official_admit_rate, r.reddit_n, r.reddit_admit_rate,
         CASE WHEN p.admit_rate > 0 AND p.admit_rate < 1 AND r.reddit_admit_rate > 0 AND r.reddit_admit_rate < 1
              THEN LEAST(8.0, GREATEST(1.0,
                     (r.reddit_admit_rate / (1 - r.reddit_admit_rate)) / (p.admit_rate / (1 - p.admit_rate))))
              ELSE 1.0 END AS odds_inflation
  FROM ADCOM.v_school_profile p
  JOIN (SELECT slug, COUNT(*) AS reddit_n, AVG(CASE WHEN outcome = 'accepted' THEN 1.0 ELSE 0.0 END) AS reddit_admit_rate
        FROM ADCOM_PG.twin_school_outcomes WHERE applicant_type = 'first_year' GROUP BY slug) r
    ON r.slug = p.slug
);

-- Radar baseline (§4.7): median admitted Reddit applicant per school
CREATE SCHEMASTORE VIEW v_admitted_medians WITH CONTAINER ADCOM AS (
  SELECT slug, COUNT(*) AS n,
         percentile_approx(gpa_uw, 0.5)                 AS gpa_uw,
         percentile_approx(sat_score, 0.5)              AS sat,
         percentile_approx(advanced_courses, 0.5)       AS advanced,
         percentile_approx(tier_derived_ec_rating, 0.5) AS ec_rating,
         percentile_approx(2 * tier1 + tier2, 0.5)      AS spike_points
  FROM ADCOM_PG.twin_school_outcomes
  WHERE outcome = 'accepted' AND applicant_type = 'first_year'
  GROUP BY slug
);

-- How a school compares with its peer group (the fact-checker's favorite query)
CREATE SCHEMASTORE VIEW v_peer_benchmarks WITH CONTAINER ADCOM AS (
  -- Window functions, not a self-join of v_school_profile: Spark rejects that self-join (missing attributes).
  SELECT slug, name, peer_group, admit_rate, sat_composite_25, sat_composite_75,
         COUNT(*)                         OVER (PARTITION BY peer_group) AS peer_n,
         percentile_approx(admit_rate, 0.5)       OVER (PARTITION BY peer_group) AS peer_median_admit_rate,
         percentile_approx(sat_composite_75, 0.5) OVER (PARTITION BY peer_group) AS peer_median_sat_75
  FROM ADCOM.v_school_profile
);
