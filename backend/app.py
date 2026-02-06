from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import logging
from proxmox_client import ProxmoxClient
from topology_analyzer import TopologyAnalyzer

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # フロントエンドからのアクセスを許可

# 環境変数から設定を取得
PROXMOX_HOST = os.getenv('PROXMOX_HOST', 'https://localhost:8006')
PROXMOX_TOKEN_ID = os.getenv('PROXMOX_TOKEN_ID', '')
PROXMOX_TOKEN_SECRET = os.getenv('PROXMOX_TOKEN_SECRET', '')
VERIFY_SSL = os.getenv('VERIFY_SSL', 'false').lower() == 'true'

# Proxmoxクライアントの初期化
try:
    proxmox_client = ProxmoxClient(
        host=PROXMOX_HOST,
        token_id=PROXMOX_TOKEN_ID,
        token_secret=PROXMOX_TOKEN_SECRET,
        verify_ssl=VERIFY_SSL
    )
    logger.info(f"Proxmox client initialized for host: {PROXMOX_HOST}")
except Exception as e:
    logger.error(f"Failed to initialize Proxmox client: {e}")
    proxmox_client = None


@app.route('/api/health', methods=['GET'])
def health_check():
    """ヘルスチェックエンドポイント"""
    return jsonify({
        'status': 'healthy',
        'proxmox_configured': proxmox_client is not None
    })


@app.route('/api/topology', methods=['GET'])
def get_topology():
    """ネットワークトポロジデータを取得"""
    if not proxmox_client:
        return jsonify({'error': 'Proxmox client not configured'}), 500
    
    try:
        analyzer = TopologyAnalyzer(proxmox_client)
        topology = analyzer.analyze_topology()
        
        logger.info(f"Topology generated: {topology['summary']}")
        return jsonify(topology)
    
    except Exception as e:
        logger.error(f"Failed to generate topology: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/nodes', methods=['GET'])
def get_nodes():
    """Proxmoxノード一覧を取得"""
    if not proxmox_client:
        return jsonify({'error': 'Proxmox client not configured'}), 500
    
    try:
        nodes = proxmox_client.get_nodes()
        return jsonify(nodes)
    
    except Exception as e:
        logger.error(f"Failed to get nodes: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/nodes/<node>/network', methods=['GET'])
def get_node_network(node):
    """指定ノードのネットワーク設定を取得"""
    if not proxmox_client:
        return jsonify({'error': 'Proxmox client not configured'}), 500
    
    try:
        network = proxmox_client.get_node_network(node)
        return jsonify(network)
    
    except Exception as e:
        logger.error(f"Failed to get network for node {node}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/nodes/<node>/vms', methods=['GET'])
def get_node_vms(node):
    """指定ノードのVM一覧を取得"""
    if not proxmox_client:
        return jsonify({'error': 'Proxmox client not configured'}), 500
    
    try:
        vms = proxmox_client.get_vms(node)
        return jsonify(vms)
    
    except Exception as e:
        logger.error(f"Failed to get VMs for node {node}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/cluster/status', methods=['GET'])
def get_cluster_status():
    """クラスタステータスを取得"""
    if not proxmox_client:
        return jsonify({'error': 'Proxmox client not configured'}), 500
    
    try:
        status = proxmox_client.get_cluster_status()
        return jsonify(status)
    
    except Exception as e:
        logger.error(f"Failed to get cluster status: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/config', methods=['GET'])
def get_config():
    """現在の設定情報を取得"""
    return jsonify({
        'proxmox_host': PROXMOX_HOST,
        'verify_ssl': VERIFY_SSL,
        'configured': proxmox_client is not None
    })


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'false').lower() == 'true'
    
    logger.info(f"Starting Flask server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)
