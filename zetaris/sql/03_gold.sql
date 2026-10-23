-- zetaris/sql/03_gold.sql: hot-path materialization (re-run INSERT OVERWRITE after each data refresh) ---
CREATE TABLE ADCOM_LAKE.gold.school_profile USING iceberg AS SELECT * FROM ADCOM.v_school_profile;
-- refresh:
INSERT OVERWRITE ADCOM_LAKE.gold.school_profile SELECT * FROM ADCOM.v_school_profile;
