#!/bin/bash

# Hyper-RAG 日志查看脚本
# 使用 tail 命令查看 Docker 容器日志

set -e

echo "=================================="
echo "   Hyper-RAG 日志查看工具"
echo "=================================="
echo ""

# 检查服务是否运行
if ! docker ps | grep -q "hyperrag-backend"; then
    echo "错误: 服务未运行，请先启动服务"
    echo "使用命令: ./start.sh"
    exit 1
fi

echo "请选择要查看的服务日志:"
echo "1) 所有服务"
echo "2) 后端服务 (Backend)"
echo "3) 前端服务 (Frontend)"
echo "4) Nginx"
echo "5) 实时查看容器内日志 (使用 tail -f)"
echo ""
read -p "请输入选项 (1-5): " choice

case $choice in
    1)
        echo ""
        echo "查看所有服务日志 (按 Ctrl+C 退出)..."
        sleep 1
        docker compose logs -f
        ;;
    2)
        echo ""
        echo "查看后端服务日志 (按 Ctrl+C 退出)..."
        sleep 1
        docker compose logs -f backend
        ;;
    3)
        echo ""
        echo "查看前端服务日志 (按 Ctrl+C 退出)..."
        sleep 1
        docker compose logs -f frontend
        ;;
    4)
        echo ""
        echo "查看 Nginx 日志 (按 Ctrl+C 退出)..."
        sleep 1
        docker compose logs -f nginx
        ;;
    5)
        echo ""
        echo "选择要查看的容器:"
        echo "1) Backend"
        echo "2) Frontend"
        echo "3) Nginx"
        read -p "请输入选项 (1-3): " container_choice

        case $container_choice in
            1)
                CONTAINER="hyperrag-backend"
                LOG_FILE="/var/log/backend.log"
                ;;
            2)
                CONTAINER="hyperrag-frontend"
                LOG_FILE="/var/log/frontend.log"
                ;;
            3)
                CONTAINER="hyperrag-nginx"
                LOG_FILE="/var/log/nginx/access.log"
                ;;
            *)
                echo "无效选项"
                exit 1
                ;;
        esac

        echo ""
        echo "在容器 $CONTAINER 中使用 tail -f 查看日志..."
        echo "注意: 如果日志文件不存在，将显示容器的标准输出"
        sleep 1

        # 尝试 tail 日志文件，如果失败则查看标准输出
        docker exec -it $CONTAINER sh -c "tail -f $LOG_FILE 2>/dev/null || tail -f /proc/1/fd/1"
        ;;
    *)
        echo "无效选项"
        exit 1
        ;;
esac
