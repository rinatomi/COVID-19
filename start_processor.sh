#!/bin/bash
cd /opt/covid-analysis/data-processor
/opt/spark/bin/spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.3.1 covid_processor.py >> processor.log 2>&1 &
echo "数据处理器已启动"