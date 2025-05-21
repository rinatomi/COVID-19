#!/bin/bash
cd /opt/covid-analysis/api-service
nohup python3 app.py > api.log 2>&1 &
echo "API服务已启动"