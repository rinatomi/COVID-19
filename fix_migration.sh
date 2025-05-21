#!/bin/bash
# 修复特定表的数据迁移

DB_USER="covid_user"
DB_PASS="ROOT050313cel*"
DB_NAME="covid_analysis"

echo "开始修复失败的表迁移..."
echo "======================================"

# 创建修复SQL
cat > fix_migration.sql << EOL
-- 禁用外键检查
SET FOREIGN_KEY_CHECKS=0;

-- 从 continent_stats 迁移到新的 continent_stats
-- 使用NOW()和UNIX_TIMESTAMP()替代可能不存在的timestamp字段
TRUNCATE TABLE continent_stats;
INSERT INTO continent_stats (
    collected_at, continent, updated, cases, today_cases,
    deaths, today_deaths, recovered, active
)
SELECT 
    NOW() as collected_at,
    continent,
    UNIX_TIMESTAMP() as updated,
    total_cases as cases,
    today_cases,
    total_deaths as deaths,
    today_deaths,
    total_recovered as recovered,
    active_cases as active
FROM (
    SELECT * FROM continent_stats LIMIT 1
) as sample_continent;

-- 从 vaccine_stats 迁移到 daily_vaccine_global
TRUNCATE TABLE daily_vaccine_global;
INSERT INTO daily_vaccine_global (stat_date, doses)
SELECT 
    date as stat_date,
    total_vaccinations as doses
FROM vaccine_stats;

-- 启用外键检查
SET FOREIGN_KEY_CHECKS=1;
EOL

# 执行修复脚本
echo "执行修复SQL..."
mysql -u $DB_USER -p$DB_PASS $DB_NAME < fix_migration.sql
if [ $? -ne 0 ]; then
    echo "警告: 修复过程中遇到问题，可能需要手动检查"
else
    echo "修复SQL执行成功"
fi

# 验证修复结果
echo "验证修复结果..."
mysql -u $DB_USER -p$DB_PASS $DB_NAME << EOF
SELECT 'continent_stats' as table_name, COUNT(*) as row_count FROM continent_stats UNION
SELECT 'daily_vaccine_global', COUNT(*) FROM daily_vaccine_global;
EOF

echo "======================================"
echo "修复操作完成！"
echo ""
echo "接下来操作："
echo "1. 如果上面显示的数据量仍然为0，可能需要手动添加数据或等待系统自动从API获取"
echo "2. 停止现有服务: ./stop_all.sh"
echo "3. 启动新的服务: ./start_all.sh"
echo "4. 服务启动后，系统将自动从API获取最新数据填充所有表" 