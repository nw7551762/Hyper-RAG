#!/bin/bash

# Hyper-RAG 啟動腳本（簡化版）
set -e

COMPOSE_FILE="docker-compose.prod.yaml"

echo "=================================="
echo "     Hyper-RAG 啟動腳本（簡化版）"
echo "=================================="
echo ""

# Check docker
if ! command -v docker &> /dev/null; then
    echo "錯誤: Docker 未安裝"
    exit 1
fi

# Check docker compose
if ! command -v docker compose &> /dev/null && ! command -v docker-compose &> /dev/null; then
    echo "錯誤: Docker Compose 未安裝"
    exit 1
fi

echo "是否需要重新 build？"
echo "0) 不 build，直接啟動"
echo "1) 重新 build 再啟動"
read -p "輸入選項 (0/1): " rebuild

if [[ $rebuild == "1" ]]; then
    echo "➡️ 重新 build 並啟動..."
    docker compose -f $COMPOSE_FILE build --no-cache
    docker compose -f $COMPOSE_FILE up -d
else
    echo "➡️ 不重新 build，直接啟動..."
    docker compose -f $COMPOSE_FILE up -d
fi

echo ""
echo "✔️ 服務啟動完成"
echo ""
echo "前端: http://localhost:5000"
echo "後端: http://localhost:5000/api"
echo "Docs: http://localhost:5000/docs"
echo ""
echo "查看所有日志: docker compose -f $COMPOSE_FILE logs -f"
echo ""

read -p "是否立即查看日志？(y/n): " view_logs

if [[ $view_logs == "y" || $view_logs == "Y" ]]; then
    docker compose -f $COMPOSE_FILE logs -f
fi
