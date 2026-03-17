#!/bin/bash

# Proxmox Network Topology クイックスタートスクリプト

echo "=========================================="
echo "Proxmox Network Topology Visualizer"
echo "=========================================="
echo ""

# .envファイルの存在チェック
if [ ! -f .env ]; then
    echo "⚠️  .env file not found!"
    echo "Creating from .env.example..."
    cp .env.example .env
    echo ""
    echo "📝 Please edit .env file with your Proxmox credentials:"
    echo "   - PROXMOX_HOST"
    echo "   - PROXMOX_TOKEN_ID"
    echo "   - PROXMOX_TOKEN_SECRET"
    echo ""
    echo "Then run this script again."
    exit 1
fi

# 環境変数の読み込み
source .env

# 設定確認
echo "📋 Configuration:"
echo "   Proxmox Host: $PROXMOX_HOST"
echo "   Token ID: $PROXMOX_TOKEN_ID"
echo "   Verify SSL: $VERIFY_SSL"
echo ""

# Docker起動確認
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed!"
    echo "Please install Docker first: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed!"
    echo "Please install Docker Compose first: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "🐳 Docker and Docker Compose found!"
echo ""

# 既存のコンテナを停止
echo "🛑 Stopping existing containers..."
docker-compose down

# コンテナをビルド＆起動
echo "🔨 Building and starting containers..."
docker-compose up -d --build

# 起動を待つ
echo "⏳ Waiting for services to start..."
sleep 10

# ヘルスチェック
echo "🏥 Checking backend health..."
if curl -s http://localhost:5000/api/health > /dev/null; then
    echo "✅ Backend is healthy!"
else
    echo "⚠️  Backend might not be ready yet. Check logs with: docker-compose logs backend"
fi

echo ""
echo "=========================================="
echo "✅ Deployment complete!"
echo "=========================================="
echo ""
echo "📊 Access the dashboard at: http://localhost"
echo "🔧 Backend API at: http://localhost:5000"
echo ""
echo "Useful commands:"
echo "  View logs:     docker-compose logs -f"
echo "  Stop:          docker-compose stop"
echo "  Restart:       docker-compose restart"
echo "  Remove:        docker-compose down"
echo ""
