-- 迁移数据脚本
-- 这个脚本用于将旧表数据迁移到新表结构
-- 执行前请确保：
-- 1. 已备份数据库
-- 2. 已执行 new_create_tables.sql 创建新表

-- 禁用外键检查，以便在迁移过程中不会受到外键约束的影响
SET FOREIGN_KEY_CHECKS=0;

-- 1. 从 global_stats 迁移到 realtime_global_stats
INSERT INTO realtime_global_stats (
    collected_at, updated, cases, today_cases, deaths, 
    today_deaths, recovered, today_recovered, active, critical
)
SELECT 
    FROM_UNIXTIME(timestamp) as collected_at, 
    timestamp as updated,
    total_cases as cases, 
    today_cases, 
    total_deaths as deaths, 
    today_deaths, 
    total_recovered as recovered, 
    today_recovered, 
    active_cases as active, 
    critical_cases as critical
FROM global_stats;

-- 2. 从 country_stats 抽取唯一国家信息填充 country 表
-- 先插入基本信息，后续可通过 data_collector 更新完整信息
INSERT IGNORE INTO country (country_code, country_name)
SELECT DISTINCT 
    country_code, 
    country
FROM country_stats
WHERE country_code IS NOT NULL AND country_code != '';

-- 3. 从 country_stats 迁移到 realtime_country_stats
INSERT INTO realtime_country_stats (
    collected_at, country_code, updated, cases, today_cases,
    deaths, today_deaths, recovered, active
)
SELECT 
    FROM_UNIXTIME(timestamp) as collected_at,
    country_code,
    timestamp as updated,
    total_cases as cases,
    today_cases,
    total_deaths as deaths,
    today_deaths,
    total_recovered as recovered,
    active_cases as active
FROM country_stats
WHERE country_code IS NOT NULL AND country_code != '';

-- 4. 从 continent_stats 迁移到新的 continent_stats
-- 注意：需要根据旧表的实际字段名调整
INSERT INTO continent_stats (
    collected_at, continent, updated, cases, today_cases,
    deaths, today_deaths, recovered, active
)
SELECT 
    NOW() as collected_at, -- 使用当前时间替代缺失的 timestamp
    continent,
    UNIX_TIMESTAMP() as updated, -- 使用当前时间戳
    total_cases as cases,
    today_cases,
    total_deaths as deaths,
    today_deaths,
    total_recovered as recovered,
    active_cases as active
FROM continent_stats;

-- 5. 从 vaccine_stats 迁移到 daily_vaccine_global
-- 注意：可能需要根据旧表的实际字段名调整
INSERT INTO daily_vaccine_global (stat_date, doses)
SELECT 
    date as stat_date,
    total_vaccinations as doses
FROM vaccine_stats;

-- 启用外键检查
SET FOREIGN_KEY_CHECKS=1;

-- 注意：其他表如 daily_global_history, daily_country_history 和 daily_vaccine_country
-- 需要通过 data_collector 重新从 API 获取数据，因为旧表结构中没有对应数据 