#!/bin/bash
# 系统更新和重启脚本
# 此脚本应用所有优化和修复，并重启COVID-19数据分析系统服务

set -e # 遇到错误立即退出
echo "=== COVID-19 分析系统更新脚本 ==="
echo "此脚本将应用所有系统更新并重启服务"
echo

# 确保工作目录正确
cd /opt/covid-analysis

# 定义颜色输出
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # 无颜色

# 函数：输出带有颜色的消息
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 函数：检查上一个命令的执行结果
check_result() {
    if [ $? -eq 0 ]; then
        log_info "$1"
    else
        log_error "$2"
        exit 1
    fi
}

# 检查权限
if [ "$(id -u)" != "0" ]; then
   log_error "此脚本必须以root权限运行"
   exit 1
fi

# 停止所有服务
log_info "停止所有服务..."
bash /opt/covid-analysis/stop_all.sh
check_result "所有服务已停止" "停止服务失败"

# 备份当前文件
log_info "备份现有文件..."
NOW=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="/opt/covid-analysis/backup_$NOW"
mkdir -p $BACKUP_DIR

cp /opt/covid-analysis/api-service/app.py $BACKUP_DIR/
cp /opt/covid-analysis/data-processor/covid_processor.py $BACKUP_DIR/
cp /opt/covid-analysis/data-collector/data_collector.py $BACKUP_DIR/

check_result "文件备份完成: $BACKUP_DIR" "文件备份失败"

# 应用修复的app.py
log_info "更新API服务..."
cp app.py /opt/covid-analysis/api-service/
check_result "API服务更新完成" "API服务更新失败"

# 应用修复的covid_processor.py
log_info "更新数据处理器..."
cp covid_processor.py /opt/covid-analysis/data-processor/
check_result "数据处理器更新完成" "数据处理器更新失败"

# 应用修复的data_collector.py
log_info "更新数据收集器..."
cp data_collector.py /opt/covid-analysis/data-collector/
check_result "数据收集器更新完成" "数据收集器更新失败"

# 复制坐标更新脚本
log_info "添加坐标更新脚本..."
cp update_coordinates.py /opt/covid-analysis/
chmod +x /opt/covid-analysis/update_coordinates.py
check_result "坐标更新脚本添加完成" "坐标更新脚本添加失败"

# 运行坐标更新脚本
log_info "更新国家地理坐标数据..."
python3 /opt/covid-analysis/update_coordinates.py
check_result "地理坐标更新完成" "地理坐标更新失败"

# 清理任何僵尸进程
log_info "清理任何僵尸进程..."
pkill -f "app.py" || true
pkill -f "covid_processor.py" || true
pkill -f "data_collector.py" || true
sleep 2

# 启动所有服务
log_info "启动所有服务..."
bash /opt/covid-analysis/start_all.sh
check_result "所有服务已启动" "启动服务失败"

# 显示服务状态
log_info "检查服务状态..."
sleep 5
ps aux | grep -E "app.py|covid_processor.py|data_collector.py" | grep -v grep

# 测试API可访问性
log_info "测试API可访问性..."
curl -s http://localhost:5000/api/health | grep "healthy" > /dev/null
check_result "API服务正常运行" "API服务无法访问"

log_info "系统更新完成！"
echo
echo "=========================="
echo "现在API提供以下新功能："
echo "1. TopN API: http://localhost:5000/api/countries/top/20"
echo "2. 健康检查: http://localhost:5000/api/health"
echo "3. 地图数据已包含正确地理坐标"
echo "==========================" 