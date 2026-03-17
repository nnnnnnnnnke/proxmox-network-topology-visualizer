from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import logging
import threading
import time
from proxmox_client import ProxmoxClient
from topology_analyzer import TopologyAnalyzer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

PROXMOX_HOST = os.getenv('PROXMOX_HOST', 'https://localhost:8006')
PROXMOX_TOKEN_ID = os.getenv('PROXMOX_TOKEN_ID', '')
PROXMOX_TOKEN_SECRET = os.getenv('PROXMOX_TOKEN_SECRET', '')
VERIFY_SSL = os.getenv('VERIFY_SSL', 'false').lower() == 'true'
CACHE_TTL = int(os.getenv('CACHE_TTL', '30'))

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


# --- Topology Cache ---
class TopologyCache:
    def __init__(self, client, ttl=30):
        self.client = client
        self.ttl = ttl
        self._cache = {}       # key -> topology data
        self._timestamps = {}  # key -> last update time
        self._locks = {}       # key -> threading.Lock
        self._updating = {}    # key -> bool
        self._global_lock = threading.Lock()

    def _get_lock(self, key):
        with self._global_lock:
            if key not in self._locks:
                self._locks[key] = threading.Lock()
                self._updating[key] = False
            return self._locks[key]

    def _cache_key(self, hide_stopped, hide_hosts_edges, hide_physical_node):
        return f"{hide_stopped}:{hide_hosts_edges}:{hide_physical_node}"

    def _build(self, hide_stopped, hide_hosts_edges, hide_physical_node, skip_agent=False):
        analyzer = TopologyAnalyzer(self.client)
        return analyzer.analyze_topology(
            hide_stopped=hide_stopped,
            hide_hosts_edges=hide_hosts_edges,
            hide_physical_node=hide_physical_node,
            skip_agent=skip_agent
        )

    def get(self, hide_stopped, hide_hosts_edges, hide_physical_node):
        key = self._cache_key(hide_stopped, hide_hosts_edges, hide_physical_node)
        now = time.time()

        # キャッシュが有効ならそのまま返す
        if key in self._cache and (now - self._timestamps.get(key, 0)) < self.ttl:
            return self._cache[key]

        # キャッシュはあるがTTL切れ → キャッシュを返しつつバックグラウンド更新
        if key in self._cache:
            self._trigger_background_update(key, hide_stopped, hide_hosts_edges, hide_physical_node)
            return self._cache[key]

        # キャッシュなし（初回） → Agent抜きで高速取得して返し、フル版をバックグラウンド更新
        try:
            data = self._build(hide_stopped, hide_hosts_edges, hide_physical_node, skip_agent=True)
            self._cache[key] = data
            self._timestamps[key] = now
            logger.info(f"Cache populated (fast, no agent): {key}")
        except Exception as e:
            logger.error(f"Failed to build topology: {e}")
            raise

        # Agent付きフル版をバックグラウンドで取得
        self._trigger_background_update(key, hide_stopped, hide_hosts_edges, hide_physical_node)
        return data

    def _trigger_background_update(self, key, hide_stopped, hide_hosts_edges, hide_physical_node):
        lock = self._get_lock(key)
        with lock:
            if self._updating.get(key):
                return
            self._updating[key] = True

        def update():
            try:
                data = self._build(hide_stopped, hide_hosts_edges, hide_physical_node, skip_agent=False)
                self._cache[key] = data
                self._timestamps[key] = time.time()
                logger.info(f"Cache updated (full): {key}")
            except Exception as e:
                logger.error(f"Background cache update failed: {e}")
            finally:
                with lock:
                    self._updating[key] = False

        thread = threading.Thread(target=update, daemon=True)
        thread.start()

    def invalidate(self):
        self._cache.clear()
        self._timestamps.clear()


topology_cache = TopologyCache(proxmox_client, ttl=CACHE_TTL) if proxmox_client else None

# Gunicorn起動時にキャッシュをウォームアップ
def warmup_cache():
    if topology_cache:
        logger.info("Warming up topology cache...")
        try:
            topology_cache.get(True, True, True)
            logger.info("Cache warmup complete")
        except Exception as e:
            logger.error(f"Cache warmup failed: {e}")

warmup_thread = threading.Thread(target=warmup_cache, daemon=True)
warmup_thread.start()


@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'proxmox_configured': proxmox_client is not None
    })


@app.route('/api/topology', methods=['GET'])
def get_topology():
    if not proxmox_client or not topology_cache:
        return jsonify({'error': 'Proxmox client not configured'}), 500

    try:
        hide_stopped = request.args.get('hide_stopped', 'true').lower() == 'true'
        hide_hosts_edges = request.args.get('hide_hosts_edges', 'true').lower() == 'true'
        hide_physical_node = request.args.get('hide_physical_node', 'true').lower() == 'true'

        topology = topology_cache.get(hide_stopped, hide_hosts_edges, hide_physical_node)
        logger.info(f"Topology served: {topology['summary']}")
        return jsonify(topology)

    except Exception as e:
        logger.error(f"Failed to generate topology: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/nodes', methods=['GET'])
def get_nodes():
    if not proxmox_client:
        return jsonify({'error': 'Proxmox client not configured'}), 500
    try:
        return jsonify(proxmox_client.get_nodes())
    except Exception as e:
        logger.error(f"Failed to get nodes: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/nodes/<node>/network', methods=['GET'])
def get_node_network(node):
    if not proxmox_client:
        return jsonify({'error': 'Proxmox client not configured'}), 500
    try:
        return jsonify(proxmox_client.get_node_network(node))
    except Exception as e:
        logger.error(f"Failed to get network for node {node}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/nodes/<node>/vms', methods=['GET'])
def get_node_vms(node):
    if not proxmox_client:
        return jsonify({'error': 'Proxmox client not configured'}), 500
    try:
        return jsonify(proxmox_client.get_vms(node))
    except Exception as e:
        logger.error(f"Failed to get VMs for node {node}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/config', methods=['GET'])
def get_config():
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
