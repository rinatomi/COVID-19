#!/bin/bash
# COVID分析系统服务停止脚本
# 用于停止所有相关服务进程

echo "开始停止所有COVID分析系统服务..."

# 停止API服务
echo "停止API服务..."
pkill -f "python3 .*app.py"
echo "API服务已停止"

# 停止数据收集器
echo "停止数据收集器..."
pkill -f "python3 .*data_collector.py"
echo "数据收集器已停止"

# 停止Spark处理器
echo "停止Spark处理器..."
pkill -f "spark-submit"
pkill -f "python3 .*covid_processor.py"
echo "Spark处理器已停止"

# 停止Kafka服务
echo "停止Kafka服务..."
cd /opt/kafka
bin/kafka-server-stop.sh
echo "Kafka服务已停止"

# 等待Kafka完全停止
sleep 5

# 停止Zookeeper服务
echo "停止Zookeeper服务..."
cd /opt/kafka
bin/zookeeper-server-stop.sh
echo "Zookeeper服务已停止"

# 先尝试正常终止所有COVID相关Python进程
echo "尝试正常终止所有COVID相关Python进程..."
pkill -f "python3 .*covid-analysis"
pkill -f "python3 .*app.py"
pkill -f "python3 .*data_collector.py"
pkill -f "python3 .*covid_processor.py"

# 给进程一些时间来正常关闭
sleep 3

# 检查是否还有遗留的Python进程
echo "检查是否有遗留的COVID相关Python进程..."
# 使用更广泛的搜索来查找任何可能的COVID分析相关Python进程
PYTHON_PROCESSES=$(ps -ef | grep -E 'python3.*(app\.py|data_collector\.py|covid_processor\.py|covid-analysis)' | grep -v grep)

if [ -n "$PYTHON_PROCESSES" ]; then
    echo "发现以下Python进程仍在运行:"
    echo "$PYTHON_PROCESSES"
    echo "正在强制终止所有相关Python进程..."
    pkill -9 -f "python3.*(app\.py|data_collector\.py|covid_processor\.py|covid-analysis)"
    echo "所有相关Python进程已强制终止"
else
    echo "没有发现遗留的COVID相关Python进程"
fi

# 最后检查任何Python进程，可能与COVID分析系统相关但没有明确标识
echo "检查是否有任何可能相关的Python进程..."
REMAINING_PYTHON=$(ps -ef | grep 'python3' | grep -v 'grep')

if [ -n "$REMAINING_PYTHON" ]; then
    echo "警告: 以下Python进程仍在运行 (可能与系统相关):"
    echo "$REMAINING_PYTHON"
    echo "请确认这些进程是否应该终止。如需终止所有Python进程，请运行: sudo killall -9 python3"
fi

# 确认所有服务已停止
echo "确认服务状态..."
sleep 2

# 检查API服务
if pgrep -f "python3 .*app.py" > /dev/null; then
    echo "警告: API服务仍在运行!"
    echo "运行以下命令强制终止: sudo pkill -9 -f \"python3 .*app.py\""
else
    echo "确认: API服务已停止"
fi

# 检查数据收集器
if pgrep -f "python3 .*data_collector.py" > /dev/null; then
    echo "警告: 数据收集器仍在运行!"
    echo "运行以下命令强制终止: sudo pkill -9 -f \"python3 .*data_collector.py\""
else
    echo "确认: 数据收集器已停止"
fi

# 检查Spark处理器
if pgrep -f "spark-submit" > /dev/null || pgrep -f "python3 .*covid_processor.py" > /dev/null; then
    echo "警告: Spark处理器仍在运行!"
    echo "运行以下命令强制终止: sudo pkill -9 -f \"spark-submit\" && sudo pkill -9 -f \"python3 .*covid_processor.py\""
else
    echo "确认: Spark处理器已停止"
fi

echo "所有COVID分析系统服务已停止" 