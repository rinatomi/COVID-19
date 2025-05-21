#!/bin/bash
cd /opt/covid-analysis/data-collector
python3 data_collector.py >> collector.log 2>&1 &
echo "数据收集器已启动"