#!/bin/bash
cd /opt/covid-analysis

# 启动Zookeeper服务
echo "启动Zookeeper服务..."
cd /opt/kafka
bin/zookeeper-server-start.sh -daemon config/zookeeper.properties
echo "Zookeeper服务已启动"

# 等待Zookeeper完全启动
sleep 5

# 启动Kafka服务
echo "启动Kafka服务..."
cd /opt/kafka
bin/kafka-server-start.sh -daemon config/server.properties
echo "Kafka服务已启动"

# 等待Kafka完全启动
sleep 5

# 返回项目目录
cd /opt/covid-analysis

# 启动数据收集器
echo "启动数据收集器..."
./data-collector/start_collector.sh

# 启动数据处理器
echo "启动数据处理器..."
./data-processor/start_processor.sh

# 启动API服务
echo "启动API服务..."
./api-service/start_api.sh

echo "所有服务已启动"