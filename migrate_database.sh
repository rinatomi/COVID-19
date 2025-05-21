#!/bin/bash
# 数据库迁移执行脚本
# 请在执行前修改数据库连接信息

DB_USER="covid_user"
DB_PASS="ROOT050313cel*"
DB_NAME="covid_analysis"
BACKUP_FILE="covid_data_backup_$(date +%Y%m%d%H%M%S).sql"

echo "开始数据库迁移..."
echo "======================================"

# 1. 备份当前数据库
echo "备份当前数据库 -> $BACKUP_FILE"
mysqldump -u $DB_USER -p$DB_PASS $DB_NAME > $BACKUP_FILE
if [ $? -ne 0 ]; then
    echo "警告: 数据库备份可能不完整，但会继续执行迁移"
fi
echo "数据库备份步骤完成"

# 2. 记录旧表数据量
echo "记录旧表数据量以便验证"
mysql -u $DB_USER -p$DB_PASS $DB_NAME << EOF
SELECT 'global_stats' as table_name, COUNT(*) as row_count FROM global_stats UNION
SELECT 'country_stats', COUNT(*) FROM country_stats UNION
SELECT 'continent_stats', COUNT(*) FROM continent_stats UNION
SELECT 'vaccine_stats', COUNT(*) FROM vaccine_stats;
EOF

# 3. 创建新表结构（现在包含DROP TABLE语句）
echo "删除现有表并创建新表结构..."
mysql -u $DB_USER -p$DB_PASS $DB_NAME < new_create_tables.sql
if [ $? -ne 0 ]; then
    echo "警告: 表结构创建过程中遇到问题，但会继续执行数据迁移"
else
    echo "新表结构创建成功"
fi

# 4. 迁移数据
echo "开始数据迁移..."
mysql -u $DB_USER -p$DB_PASS $DB_NAME < migrate_data.sql
if [ $? -ne 0 ]; then
    echo "警告: 数据迁移过程中遇到问题，请检查数据完整性"
else
    echo "数据迁移成功完成"
fi

# 5. 验证数据迁移结果
echo "验证新表数据量"
mysql -u $DB_USER -p$DB_PASS $DB_NAME << EOF
SELECT 'realtime_global_stats' as table_name, COUNT(*) as row_count FROM realtime_global_stats UNION
SELECT 'country', COUNT(*) FROM country UNION
SELECT 'realtime_country_stats', COUNT(*) FROM realtime_country_stats UNION
SELECT 'continent_stats', COUNT(*) FROM continent_stats UNION
SELECT 'daily_vaccine_global', COUNT(*) FROM daily_vaccine_global;
EOF

echo "======================================"
echo "数据库迁移已完成！"
echo ""
echo "后续操作："
echo "1. 请检查上面显示的表行数，确保数据正确迁移"
echo "2. 停止现有服务: ./stop_all.sh"
echo "3. 启动新的服务: ./start_all.sh"
echo "4. 服务启动后，系统将自动从API获取历史数据填充新表"
echo ""
echo "注意: 如果上面的表行数显示为0或明显错误，请检查迁移日志并手动修复问题" 