-- 先删除所有表（如果存在）
-- 注意删除顺序：先删除有外键约束的表，最后删除基础表

-- 删除国家疫苗数据表（有外键）
DROP TABLE IF EXISTS daily_vaccine_country;

-- 删除国家历史趋势表（有外键）
DROP TABLE IF EXISTS daily_country_history;

-- 删除国家实时数据表（有外键）
DROP TABLE IF EXISTS realtime_country_stats;

-- 删除其他表（无外键或是基础表）
DROP TABLE IF EXISTS continent_stats;
DROP TABLE IF EXISTS daily_vaccine_global;
DROP TABLE IF EXISTS daily_global_history;
DROP TABLE IF EXISTS realtime_global_stats;
DROP TABLE IF EXISTS country;

-- 1. 国家维度表
CREATE TABLE country (
    country_code VARCHAR(5) PRIMARY KEY,  -- ISO2，如 CN
    country_name VARCHAR(100),
    iso3 VARCHAR(5),
    geo_id INT,
    latitude FLOAT,
    longitude FLOAT,
    continent VARCHAR(50),
    flag_url VARCHAR(255),
    latest_population BIGINT
);

-- 2. 全球实时数据表
CREATE TABLE realtime_global_stats (
    collected_at DATETIME PRIMARY KEY,       -- 插入时间
    updated BIGINT,                          -- disease.sh 更新时间戳
    cases BIGINT,
    today_cases BIGINT,
    deaths BIGINT,
    today_deaths BIGINT,
    recovered BIGINT,
    today_recovered BIGINT,
    active BIGINT,
    critical BIGINT,
    tests BIGINT,
    population BIGINT,
    affected_countries INT
);

-- 3. 全球历史趋势表
CREATE TABLE daily_global_history (
    stat_date DATE PRIMARY KEY,
    cases BIGINT,
    deaths BIGINT,
    recovered BIGINT
);

-- 4. 国家实时数据表
CREATE TABLE realtime_country_stats (
    collected_at DATETIME,
    country_code VARCHAR(5),
    updated BIGINT,
    cases BIGINT,
    today_cases BIGINT,
    deaths BIGINT,
    today_deaths BIGINT,
    recovered BIGINT,
    today_recovered BIGINT,
    active BIGINT,
    critical BIGINT,
    tests BIGINT,
    population BIGINT,
    PRIMARY KEY (collected_at, country_code),
    FOREIGN KEY (country_code) REFERENCES country(country_code)
);

-- 5. 国家历史趋势表
CREATE TABLE daily_country_history (
    stat_date DATE,
    country_code VARCHAR(5),
    cases BIGINT,
    deaths BIGINT,
    recovered BIGINT,
    PRIMARY KEY (stat_date, country_code),
    FOREIGN KEY (country_code) REFERENCES country(country_code)
);

-- 6. 全球疫苗数据表
CREATE TABLE daily_vaccine_global (
    stat_date DATE PRIMARY KEY,
    doses BIGINT
);

-- 7. 国家疫苗数据表
CREATE TABLE daily_vaccine_country (
    stat_date DATE,
    country_code VARCHAR(5),
    doses BIGINT,
    PRIMARY KEY (stat_date, country_code),
    FOREIGN KEY (country_code) REFERENCES country(country_code)
);

-- 8. 大洲实时数据表（额外保留）
CREATE TABLE continent_stats (
    collected_at DATETIME,
    continent VARCHAR(50),
    updated BIGINT,
    cases BIGINT,
    today_cases BIGINT,
    deaths BIGINT,
    today_deaths BIGINT,
    recovered BIGINT,
    active BIGINT,
    critical BIGINT,
    tests BIGINT,
    population BIGINT,
    PRIMARY KEY (collected_at, continent)
); 