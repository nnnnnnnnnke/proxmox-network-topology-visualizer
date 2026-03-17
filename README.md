# Proxmox Network Topology Visualizer

A web-based dashboard that visualizes the network topology of a Proxmox VE cluster. It runs via Docker Compose and connects to a remote Proxmox VE server through the API to display physical nodes, VMs, networks, VLANs, and IP address ranges interactively.

![Topology Overview](docs/images/topology-overview.png?v=2)

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
- **Interactive graph** — click nodes and edges to view detailed information with neighbor highlighting
- **Display filters** — toggle visibility of stopped VMs, host edges, and physical nodes
- **Custom layout** — bridges and SDN VNets arranged horizontally with VMs in semicircles below; VLAN nodes positioned between parent bridge and VMs
- **Auto-refresh** at configurable intervals (10s, 30s, 1m, 5m)
- **Detail panel** — click any node/edge to see properties (VMID, IP, CPU, memory, VLAN, MAC, SDN zone/subnet, etc.)
- **IP address detection** — automatically detects VM IPs via QEMU Guest Agent, with cloud-init / LXC config fallback
- **VLAN visualization** — VMs with VLAN tags are connected through dedicated VLAN nodes for clear network segmentation view
- **SDN details** — SDN VNets display zone type, subnet CIDR, gateway, and SNAT status
- **Multi-node support** — multiple Proxmox nodes are arranged horizontally in the layout
- **Parallel data fetching** — Guest Agent queries run concurrently for fast topology loading
- **Supported resources:**
  - Physical nodes (Proxmox servers)
  - Virtual machines (QEMU)
  - Containers (LXC)
  - Network bridges
  - VLANs (as dedicated graph nodes)
  - SDN VNETs (with zone/subnet info)
  - IP address information (Guest Agent / cloud-init / LXC)

## Prerequisites

- Proxmox VE 7.0+
- Docker & Docker Compose
- Proxmox API token
- Network access to the Proxmox server on port 8006

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

## Display Filters

The header bar provides toggles to control what is shown on the graph:

| Filter | Default | Description |
|---|---|---|
| **Hide stopped** | ON | Hide VMs/containers that are not running |
| **Hide host edges** | ON | Hide dotted lines connecting physical nodes to their VMs |
| **Hide physical node** | ON | Hide the physical Proxmox server node |

These filters are applied server-side via query parameters on the `/api/topology` endpoint.

## IP Address Detection

VM IP addresses are detected using a three-tier fallback strategy:

1. **QEMU Guest Agent** (most accurate) — queries the running VM's agent for real-time interface info. Only attempted for VMs with `agent=1` in their config. Queries run in parallel with a 3-second timeout for fast response.
2. **Cloud-init config** — extracts static IPs from `ipconfig` settings in the VM configuration.
3. **LXC container config** — extracts IPs from LXC `net` configuration entries.

> **Tip:** Install `qemu-guest-agent` in your VMs and enable the agent in the VM config (`Options → QEMU Guest Agent → Enable`) for the most accurate IP detection.

## API Endpoints

Accessible via Nginx at `http://localhost/api/*`:

| Endpoint | Description |
|---|---|
| `GET /api/health` | Health check |
| `GET /api/topology?hide_stopped=true&hide_hosts_edges=true&hide_physical_node=true` | Full topology data (with filters) |
| `GET /api/nodes` | List of nodes |
| `GET /api/nodes/<node>/network` | Node network configuration |
| `GET /api/nodes/<node>/vms` | VMs and containers on a node |
| `GET /api/config` | Current configuration |

## Graph Legend

| Color | Shape | Resource Type |
|---|---|---|
| Green | Circle | Running VM (QEMU) |
| Gray | Circle (small) | Stopped VM |
| Orange | Hexagon | LXC container |
| Indigo | Rounded rectangle | Network bridge |
| Pink | Rounded rectangle | SDN VNET |
| Cyan | Diamond | VLAN |
| Blue | Rounded rectangle | Physical node |

## Troubleshooting

### Cannot connect to Proxmox API

```bash
curl -sk https://<PROXMOX_HOST>:8006/api2/json/version \
  -H "Authorization: PVEAPIToken=<TOKEN_ID>=<TOKEN_SECRET>"
```

### View container logs

```bash
docker compose logs backend
docker compose logs frontend
```

### Topology loading is slow

The backend fetches Guest Agent data from each VM in parallel. If many VMs lack the guest agent, each times out after 3 seconds. To speed things up:
- Install and enable `qemu-guest-agent` on your VMs
- Or ensure `agent=0` (or no agent setting) in VM config to skip the query entirely

### SSL certificate errors

Set `VERIFY_SSL=false` in `.env` when using a self-signed certificate.

## Development

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
Docker Composeで起動し、リモートのProxmox VEサーバーにAPI経由で接続して、物理ノード、仮想マシン、ネットワーク、VLAN、IPアドレス帯を視覚的に表示します。

![トポロジ表示イメージ](docs/images/topology-overview.png?v=2)

## 機能

- **リアルタイムトポロジ表示**: Proxmoxクラスタ全体のネットワーク構成を視覚化
- **インタラクティブなグラフ**: ノードやエッジをクリックして詳細情報を表示（隣接ノードのハイライト付き）
- **表示フィルタ**: 停止中のVM、ホストエッジ、物理ノードの表示/非表示を切替可能
- **カスタムレイアウト**: ブリッジ・SDN VNetを水平配置し、VMを扇状に配置。VLANノードは親ブリッジとVM間に配置
- **自動更新**: 10秒〜5分の間隔で自動更新
- **詳細パネル**: ノードクリックでVMID、IP、CPU、メモリ、VLAN、MAC、SDN Zone/Subnetなどの詳細を表示
- **IPアドレス自動検出**: QEMU Guest Agent → cloud-init → LXCコンフィグの3段階フォールバックでIP取得
- **VLAN可視化**: VLANタグ付きVMは専用VLANノード（ダイヤモンド型）を経由してブリッジに接続
- **SDN詳細情報**: SDN VNetのZone種別、サブネットCIDR、ゲートウェイ、SNAT状態を表示
- **マルチノード対応**: 複数Proxmoxノードを水平に配置
- **並列データ取得**: Guest Agentクエリを並列実行し高速レスポンス

## セットアップ

### 1. Proxmox APIトークンの作成

```bash
pveum user token add user@pam tokenname --privsep=0
```

### 2. クローンと環境設定

```bash
git clone https://github.com/nnnnnnnnnke/proxmox-network-topology-visualizer.git
cd proxmox-network-topology-visualizer

cp .env.example .env
# .env を編集してProxmoxサーバーの情報を設定
```

### 3. 起動

```bash
docker compose up -d
```

ブラウザで `http://localhost` にアクセス。

## 表示フィルタ

ヘッダーバーのトグルで表示内容を制御できます：

| フィルタ | デフォルト | 説明 |
|---|---|---|
| **Hide stopped** | ON | 停止中のVM/コンテナを非表示 |
| **Hide host edges** | ON | 物理ノードとVMを結ぶ点線を非表示 |
| **Hide physical node** | ON | 物理Proxmoxサーバーノードを非表示 |

## IPアドレス検出

VMのIPアドレスは以下の優先順位で自動検出されます：

1. **QEMU Guest Agent**（最も正確）— VM内のエージェントからリアルタイムのインターフェース情報を取得。`agent=1` が設定されたVMのみ対象。3秒タイムアウトで並列実行。
2. **Cloud-init設定** — VM設定の `ipconfig` から静的IPを抽出。
3. **LXCコンテナ設定** — LXCの `net` 設定からIPを抽出。

> **ヒント:** `qemu-guest-agent` をVMにインストールし、VMオプションでQEMUゲストエージェントを有効にすると、最も正確なIP検出が可能になります。

## トラブルシューティング

### トポロジの読み込みが遅い

Guest Agentデータは並列で取得しますが、エージェント未導入のVMは3秒のタイムアウトが発生します。改善方法：
- VMに `qemu-guest-agent` をインストール・有効化する
- または VM設定で `agent=0` にしてクエリをスキップさせる

### Proxmox APIに接続できない

```bash
curl -sk https://<PROXMOX_HOST>:8006/api2/json/version \
  -H "Authorization: PVEAPIToken=<TOKEN_ID>=<TOKEN_SECRET>"
```

### コンテナのログを確認

```bash
docker compose logs backend
docker compose logs frontend
```

### SSL証明書エラー

自己署名証明書を使用している場合は `.env` で `VERIFY_SSL=false` を設定してください。

## ライセンス

[MIT License](LICENSE)
