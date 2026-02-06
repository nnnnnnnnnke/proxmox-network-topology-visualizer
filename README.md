# Proxmox Network Topology Visualizer

A web-based dashboard that visualizes the network topology of a Proxmox VE cluster. It runs on your local PC (e.g. Mac) via Docker Compose and connects to a remote Proxmox VE server through the API to display physical nodes, VMs, networks, VLANs, and IP address ranges interactively.

## Architecture

```
┌──────────────────────┐          ┌─────────────────────┐
│  Local PC (Mac, etc.) │          │  Proxmox VE Server  │
│                      │          │                     │
│  ┌────────────────┐  │  HTTPS   │  ┌───────────────┐  │
│  │ Frontend       │  │          │  │ Proxmox API   │  │
│  │ (Nginx:80)     │  │          │  │ (Port 8006)   │  │
│  └───────┬────────┘  │          │  └───────────────┘  │
│          │ /api/*    │          │                     │
│  ┌───────▼────────┐  │          │                     │
│  │ Backend        │──┼──────────┤                     │
│  │ (Flask:5000)   │  │ API Token│                     │
│  └────────────────┘  │          │                     │
│                      │          │                     │
│  (Docker Compose)    │          │                     │
└──────────────────────┘          └─────────────────────┘
```

- **Frontend (Nginx)** serves the Web UI on port 80 and proxies `/api/*` requests to the backend
- **Backend (Flask)** connects to the Proxmox VE API using token authentication to retrieve topology data
- The backend runs only within the Docker network and does not expose ports to the host

## Features

- **Real-time topology visualization** of the entire Proxmox cluster
- **Interactive graph** — click nodes and edges to view detailed information
- **Auto-refresh** at configurable intervals (10s, 30s, 1m, 5m)
- **Supported resources:**
  - Physical nodes (Proxmox servers)
  - Virtual machines (QEMU)
  - Containers (LXC)
  - Network bridges
  - VLANs
  - IP address information
  - SDN VNETs

## Prerequisites

- Proxmox VE 7.0+
- Docker & Docker Compose (on your local PC)
- Proxmox API token
- Network access from your local PC to the Proxmox server on port 8006

## Quick Start

### 1. Create a Proxmox API Token

In the Proxmox Web UI:

1. Go to **Datacenter → Permissions → API Tokens**
2. Click **Add**
3. Enter the user and token ID
4. Uncheck **Privilege Separation** (if needed)
5. Save the generated token secret

Or via CLI:
```bash
pveum user token add user@pam tokenname --privsep=0
```

### 2. Clone and Configure

```bash
git clone https://github.com/nnnnnnnnnke/proxmox-network-topology-visualizer.git
cd proxmox-network-topology-visualizer

cp .env.example .env
```

Edit `.env` with your Proxmox server details:
```bash
PROXMOX_HOST=https://192.168.1.100:8006
PROXMOX_TOKEN_ID=root@pam!topology
PROXMOX_TOKEN_SECRET=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
VERIFY_SSL=false
```

### 3. Start

```bash
docker compose up -d
```

### 4. Access

Open your browser:
```
http://localhost
```

## API Endpoints

Accessible via Nginx at `http://localhost/api/*`:

| Endpoint | Description |
|---|---|
| `GET /api/health` | Health check |
| `GET /api/topology` | Full topology data |
| `GET /api/nodes` | List of nodes |
| `GET /api/nodes/<node>/network` | Node network configuration |
| `GET /api/nodes/<node>/vms` | VMs and containers on a node |
| `GET /api/cluster/status` | Cluster status |
| `GET /api/config` | Current configuration |

## Graph Legend

| Color | Shape | Resource Type |
|---|---|---|
| Blue | Square | Physical node (Proxmox server) |
| Green | Circle | Virtual machine (QEMU VM) |
| Orange | Hexagon | LXC container |
| Purple | Diamond | Network bridge |
| Cyan | Triangle | VLAN |
| Red | Star | SDN VNET |

## Troubleshooting

### Cannot connect to Proxmox API

```bash
curl -sk https://<PROXMOX_HOST>:8006/api2/json/version \
  -H "Authorization: PVEAPIToken=<TOKEN_ID>=<TOKEN_SECRET>"
```

If the connection fails:
- Check that port 8006 is allowed in the Proxmox server firewall
- Verify VPN/Tailscale route is active
- Check API token permissions

### View container logs

```bash
docker compose logs backend
docker compose logs frontend
```

### SSL certificate errors

If using a self-signed certificate, set `VERIFY_SSL=false` in `.env`.

## Development

### Local development (without Docker)

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py

# Frontend (separate terminal)
cd frontend
npm install
npm start
```

## License

[MIT License](LICENSE)

---

# Proxmox Network Topology Visualizer (日本語)

Proxmoxクラスタのネットワークトポロジを可視化するWebベースのダッシュボードです。
手元のPC（Mac等）からリモートのProxmox VEサーバーにAPI経由で接続し、物理ノード、仮想マシン、ネットワーク、VLAN、IPアドレス帯を視覚的に表示します。

## 構成概要

```
┌──────────────────────┐          ┌─────────────────────┐
│  手元のPC (Mac等)     │          │  Proxmox VE Server  │
│                      │          │                     │
│  ┌────────────────┐  │  HTTPS   │  ┌───────────────┐  │
│  │ Frontend       │  │          │  │ Proxmox API   │  │
│  │ (Nginx:80)     │  │          │  │ (Port 8006)   │  │
│  └───────┬────────┘  │          │  └───────────────┘  │
│          │ /api/*    │          │                     │
│  ┌───────▼────────┐  │          │                     │
│  │ Backend        │──┼──────────┤                     │
│  │ (Flask:5000)   │  │ API Token│                     │
│  └────────────────┘  │          │                     │
│                      │          │                     │
│  (Docker Compose)    │          │                     │
└──────────────────────┘          └─────────────────────┘
```

- **Frontend（Nginx）** がポート80でWebUIを提供し、`/api/*` へのリクエストをBackendにプロキシ
- **Backend（Flask）** がProxmox VE APIにトークン認証で接続しトポロジデータを取得
- バックエンドはDockerネットワーク内部のみで動作し、外部にポートを公開しない

## 機能

- **リアルタイムトポロジ表示**: Proxmoxクラスタ全体のネットワーク構成を視覚化
- **インタラクティブなグラフ**: ノードやエッジをクリックして詳細情報を表示
- **自動更新**: 指定した間隔（10秒〜5分）で自動的にデータを更新
- **対応リソース**:
  - 物理ノード（Proxmoxサーバー）
  - 仮想マシン（QEMU）
  - コンテナ（LXC）
  - ネットワークブリッジ
  - VLAN設定
  - IPアドレス情報
  - SDN VNET

## 前提条件

- Proxmox VE 7.0以上
- Docker & Docker Compose（手元のPC側）
- Proxmox APIトークン
- 手元のPCからProxmoxサーバーのポート8006にアクセス可能であること

## セットアップ

### 1. Proxmox APIトークンの作成

Proxmox WebUIで以下の手順でAPIトークンを作成します：

1. Datacenter → Permissions → API Tokens
2. "Add"をクリック
3. ユーザーとトークンIDを入力
4. "Privilege Separation"のチェックを外す（必要に応じて）
5. 生成されたトークンシークレットを保存

CLI経由の場合：
```bash
pveum user token add user@pam tokenname --privsep=0
```

### 2. クローンと環境設定

```bash
git clone https://github.com/nnnnnnnnnke/proxmox-network-topology-visualizer.git
cd proxmox-network-topology-visualizer

cp .env.example .env
```

`.env` を編集してProxmoxサーバーの情報を設定：
```bash
PROXMOX_HOST=https://192.168.1.100:8006
PROXMOX_TOKEN_ID=root@pam!topology
PROXMOX_TOKEN_SECRET=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
VERIFY_SSL=false
```

### 3. 起動

```bash
docker compose up -d
```

### 4. アクセス

ブラウザで手元のPCから：
```
http://localhost
```

## トラブルシューティング

### Proxmox APIに接続できない

```bash
curl -sk https://<PROXMOX_HOST>:8006/api2/json/version \
  -H "Authorization: PVEAPIToken=<TOKEN_ID>=<TOKEN_SECRET>"
```

接続できない場合：
- Proxmoxサーバーのファイアウォールでポート8006が許可されているか確認
- VPN/Tailscale等の経路が有効か確認
- APIトークンの権限を確認

### コンテナのログを確認

```bash
docker compose logs backend
docker compose logs frontend
```

### SSL証明書エラー

自己署名証明書を使用している場合は `.env` で `VERIFY_SSL=false` を設定してください。

## ライセンス

[MIT License](LICENSE)
