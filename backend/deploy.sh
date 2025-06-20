#!/bin/bash

echo "开始部署 PersonaFlow 到腾讯云..."

# 创建必要的目录
mkdir -p data logs nginx

# 停止现有容器
echo "停止现有容器..."
docker-compose down

# 清理未使用的镜像
echo "清理未使用的镜像..."
docker image prune -f

# 构建并启动服务
echo "构建并启动服务..."
docker-compose up --build -d

# 检查服务状态
echo "检查服务状态..."
sleep 10
docker-compose ps

echo "检查服务健康状态..."
docker-compose exec personaflow-api curl -f http://localhost:8000/api/health

echo "部署完成！"
echo "API 文档: http://yixin.icu/docs"
echo "健康检查: http://yixin.icu/api/health" 