from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import logging
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
    return jsonify({
        'status': 'healthy',
        'proxmox_configured': proxmox_client is not None
    })


@app.route('/api/topology', methods=['GET'])
def get_topology():
    if not proxmox_client:
        return jsonify({'error': 'Proxmox client not configured'}), 500

    try:
        hide_stopped = request.args.get('hide_stopped', 'true').lower() == 'true'
        hide_hosts_edges = request.args.get('hide_hosts_edges', 'true').lower() == 'true'
        hide_physical_node = request.args.get('hide_physical_node', 'true').lower() == 'true'

        analyzer = TopologyAnalyzer(proxmox_client)
        topology = analyzer.analyze_topology(
            hide_stopped=hide_stopped,
            hide_hosts_edges=hide_hosts_edges,
            hide_physical_node=hide_physical_node
        )

        logger.info(f"Topology generated: {topology['summary']}")
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
