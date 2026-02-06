# Proxmox Network Topology Visualizer

Proxmoxクラスタのネットワークトポロジを可視化するWebベースのダッシュボードです。物理ノード、仮想マシン、ネットワーク、VLAN、IPアドレス帯を視覚的に表示します。

## 機能

- **リアルタイムトポロジ表示**: Proxmoxクラスタ全体のネットワーク構成を視覚化
- **インタラクティブなグラフ**: ノードやエッジをクリックして詳細情報を表示
- **自動更新**: 指定した間隔で自動的にデータを更新
- **詳細情報表示**:
  - 物理ノード（Proxmoxサーバー）
  - 仮想マシン（QEMU）
  - コンテナ（LXC）
  - ネットワークブリッジ
  - VLAN設定
  - IPアドレス情報
  - SDN VNET（設定されている場合）

## 前提条件

- Proxmox VE 7.0以上
- Docker & Docker Compose
- Proxmox APIトークン

## セットアップ

### 1. Proxmox APIトークンの作成

Proxmox WebUIで以下の手順でAPIトークンを作成します：

```bash
# CLI経由での作成例
pveum user token add user@pam tokenname --privsep=0
```

または、WebUI:
1. Datacenter → Permissions → API Tokens
2. "Add"をクリック
3. ユーザーとトークンIDを入力
4. "Privilege Separation"のチェックを外す（必要に応じて）
5. 生成されたトークンシークレットを保存

### 2. リポジトリのクローンと設定

```bash
# リポジトリをクローン
git clone <repository-url>
cd proxmox-topology

# 環境変数ファイルを作成
cp .env.example .env

# .envファイルを編集してProxmox情報を設定
nano .env
```

`.env`ファイルの設定例：
```bash
PROXMOX_HOST=https://192.168.1.100:8006
PROXMOX_TOKEN_ID=root@pam!topology
PROXMOX_TOKEN_SECRET=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
VERIFY_SSL=false
```

### 3. Docker Composeで起動

```bash
# コンテナをビルド＆起動
docker-compose up -d

# ログを確認
docker-compose logs -f
```

### 4. アクセス

ブラウザで以下のURLにアクセス：
```
http://<proxmox-server-ip>
```

## アーキテクチャ

```
┌─────────────────┐
│   Frontend      │
│   (React +      │
│   Cytoscape.js) │
│   Port: 80      │
└────────┬────────┘
         │
         │ HTTP/REST API
         │
┌────────▼────────┐
│   Backend       │
│   (Flask)       │
│   Port: 5000    │
└────────┬────────┘
         │
         │ Proxmox API
         │
┌────────▼────────┐
│   Proxmox VE    │
│   Cluster       │
└─────────────────┘
```

## API エンドポイント

バックエンドは以下のAPIエンドポイントを提供します：

- `GET /api/health` - ヘルスチェック
- `GET /api/topology` - 完全なトポロジデータ
- `GET /api/nodes` - ノード一覧
- `GET /api/nodes/<node>/network` - ノードのネットワーク設定
- `GET /api/nodes/<node>/vms` - ノードのVM一覧
- `GET /api/cluster/status` - クラスタステータス
- `GET /api/config` - 現在の設定情報

## トポロジグラフの凡例

- 🔵 **青色・四角**: 物理ノード（Proxmoxサーバー）
- 🟢 **緑色・円**: 仮想マシン（QEMU VM）
- 🟠 **オレンジ・六角形**: LXCコンテナ
- 🟣 **紫色・ダイヤ**: ネットワークブリッジ
- 🔷 **シアン・三角**: VLAN
- 🔴 **赤色・星**: SDN VNET

## カスタマイズ

### 更新間隔の変更

UIの"Auto-refresh"チェックボックスをオンにして、ドロップダウンから更新間隔を選択できます：
- 10秒
- 30秒
- 1分
- 5分

### ネットワーク表示のカスタマイズ

`frontend/src/components/TopologyView.jsx`のCytoscapeスタイル設定を編集することで、ノードやエッジの見た目をカスタマイズできます。

### レイアウトアルゴリズムの変更

デフォルトでは`cola`レイアウトを使用していますが、他のレイアウトに変更可能です：
- `grid` - グリッドレイアウト
- `circle` - 円形レイアウト
- `concentric` - 同心円レイアウト
- `breadthfirst` - 階層レイアウト

## トラブルシューティング

### 接続エラー

```bash
# バックエンドのログを確認
docker-compose logs backend

# Proxmox APIへの接続をテスト
curl -k -H "Authorization: PVEAPIToken=<TOKEN_ID>=<TOKEN_SECRET>" \
  https://<PROXMOX_HOST>:8006/api2/json/cluster/resources
```

### データが表示されない

1. APIトークンの権限を確認
2. ファイアウォール設定を確認
3. ProxmoxホストのURLが正しいか確認

### SSL証明書エラー

自己署名証明書を使用している場合は、`.env`ファイルで以下を設定：
```bash
VERIFY_SSL=false
```

## 開発

### ローカル開発環境

```bash
# バックエンド
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py

# フロントエンド
cd frontend
npm install
npm start
```

## セキュリティ上の注意

- 本番環境では適切なSSL証明書を使用してください
- APIトークンは安全に保管してください
- ネットワークアクセスを適切に制限してください
- 定期的にProxmoxとDockerイメージを更新してください

## ライセンス

MIT License

## 貢献

プルリクエストを歓迎します。大きな変更の場合は、まずissueを開いて変更内容を議論してください。

## サポート

問題が発生した場合は、GitHubのissueで報告してください。
