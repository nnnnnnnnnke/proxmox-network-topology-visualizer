# Proxmox Network Topology Visualizer

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
git clone https://github.com/nnnnnnnnnke/proxmox-topology.git
cd proxmox-topology

# 環境変数ファイルを作成
cp .env.example .env
```

`.env` を編集してProxmoxサーバーの情報を設定：
```bash
# Proxmox VEサーバーのアドレス（リモートサーバーのIP/ホスト名）
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

## API エンドポイント

Nginx経由で `http://localhost/api/*` としてアクセスできます：

| エンドポイント | 説明 |
|---|---|
| `GET /api/health` | ヘルスチェック |
| `GET /api/topology` | 完全なトポロジデータ |
| `GET /api/nodes` | ノード一覧 |
| `GET /api/nodes/<node>/network` | ノードのネットワーク設定 |
| `GET /api/nodes/<node>/vms` | ノードのVM一覧 |
| `GET /api/cluster/status` | クラスタステータス |
| `GET /api/config` | 現在の設定情報 |

## トポロジグラフの凡例

| 色 | 形 | リソースタイプ |
|---|---|---|
| 青 | 四角 | 物理ノード（Proxmoxサーバー） |
| 緑 | 円 | 仮想マシン（QEMU VM） |
| オレンジ | 六角形 | LXCコンテナ |
| 紫 | ダイヤ | ネットワークブリッジ |
| シアン | 三角 | VLAN |
| 赤 | 星 | SDN VNET |

## トラブルシューティング

### Proxmox APIに接続できない

```bash
# 手元のPCからProxmox APIへの疎通を確認
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

## 開発

### ローカル開発環境（Docker不使用）

```bash
# バックエンド
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py

# フロントエンド（別ターミナル）
cd frontend
npm install
npm start
```

## ライセンス

MIT License
