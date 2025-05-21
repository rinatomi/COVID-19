#!/bin/bash
# 强制从API获取最新数据填充所有表

echo "开始强制数据更新..."
echo "======================================"

# 1. 停止当前所有服务
echo "停止所有服务..."
./stop_all.sh
sleep 3

# 2. 确保表已创建但为空
echo "重置尚未填充的表..."
mysql -u covid_user -p"ROOT050313cel*" covid_analysis << EOF
TRUNCATE TABLE continent_stats;
TRUNCATE TABLE daily_vaccine_global;
TRUNCATE TABLE daily_global_history;
TRUNCATE TABLE daily_country_history;
TRUNCATE TABLE daily_vaccine_country;
EOF

# 3. 修改data_collector.py的行为，强制获取所有数据
echo "创建临时数据收集脚本..."
cat > force_data_collector.py << EOL
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from data_collector import (
    initialize_country_data, 
    collect_global_history, 
    collect_country_history, 
    collect_vaccine_data, 
    collect_realtime_data,
    logger
)

if __name__ == "__main__":
    logger.info("开始强制数据收集，填充所有表...")
    try:
        # 首先收集国家基础信息
        initialize_country_data()
        
        # 然后收集实时数据
        collect_realtime_data()
        
        # 收集历史数据
        collect_global_history()
        collect_country_history()
        
        # 收集疫苗数据
        collect_vaccine_data()
        
        logger.info("所有表的数据收集已完成")
    except Exception as e:
        logger.error(f"强制数据收集失败: {str(e)}")
EOL

# 4. 执行强制数据收集
echo "执行强制数据收集..."
python3 force_data_collector.py

# 5. 检查数据结果
echo "验证数据收集结果..."
mysql -u covid_user -p"ROOT050313cel*" covid_analysis << EOF
SELECT 'continent_stats' as table_name, COUNT(*) as row_count FROM continent_stats UNION
SELECT 'daily_vaccine_global', COUNT(*) FROM daily_vaccine_global UNION
SELECT 'daily_global_history', COUNT(*) FROM daily_global_history UNION
SELECT 'daily_country_history', COUNT(*) FROM daily_country_history UNION
SELECT 'daily_vaccine_country', COUNT(*) FROM daily_vaccine_country;
EOF

# 6. 启动所有服务
echo "启动所有服务..."
./start_all.sh

echo "======================================"
echo "强制数据更新完成！"
echo ""
echo "如果上面显示的表行数仍然为0，请检查日志文件以获取详细错误信息：/opt/covid-analysis/data-collector/data_collector.log" 