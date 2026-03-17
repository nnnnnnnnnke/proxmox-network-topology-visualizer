import requests
import urllib3
from typing import Dict, List, Optional
import logging

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProxmoxClient:
    """Proxmox VE API クライアント"""

    def __init__(self, host: str, token_id: str, token_secret: str, verify_ssl: bool = False):
        self.host = host.rstrip('/')
        self.verify_ssl = verify_ssl
        self.headers = {
            'Authorization': f'PVEAPIToken={token_id}={token_secret}'
        }

    def _request(self, method: str, endpoint: str, params: Optional[Dict] = None) -> Dict:
        url = f"{self.host}/api2/json{endpoint}"
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                params=params,
                verify=self.verify_ssl,
                timeout=10
            )
            response.raise_for_status()
            return response.json().get('data', {})
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise

    def get_nodes(self) -> List[Dict]:
        return self._request('GET', '/cluster/resources', {'type': 'node'})

    def get_node_network(self, node: str) -> List[Dict]:
        return self._request('GET', f'/nodes/{node}/network')

    def get_vms(self, node: str) -> List[Dict]:
        qemu_vms = self._request('GET', f'/nodes/{node}/qemu')
        lxc_containers = self._request('GET', f'/nodes/{node}/lxc')
        return qemu_vms + lxc_containers

    def get_vm_config(self, node: str, vmid: int, vm_type: str = 'qemu') -> Dict:
        return self._request('GET', f'/nodes/{node}/{vm_type}/{vmid}/config')

    def get_vm_agent_interfaces(self, node: str, vmid: int) -> List[Dict]:
        """QEMU Guest Agent経由でVMの実際のネットワークインターフェース情報を取得"""
        try:
            result = self._request('GET', f'/nodes/{node}/qemu/{vmid}/agent/network-get-interfaces')
            return result.get('result', []) if isinstance(result, dict) else result
        except Exception as e:
            logger.debug(f"Guest agent not available for VM {vmid}: {e}")
            return []

    def get_cluster_status(self) -> Dict:
        return self._request('GET', '/cluster/status')

    def get_sdn_vnets(self) -> List[Dict]:
        try:
            return self._request('GET', '/cluster/sdn/vnets')
        except Exception as e:
            logger.warning(f"SDN not available or configured: {e}")
            return []

    def get_sdn_zones(self) -> List[Dict]:
        try:
            return self._request('GET', '/cluster/sdn/zones')
        except Exception as e:
            logger.warning(f"SDN zones not available: {e}")
            return []

    def get_sdn_subnets(self, vnet: str) -> List[Dict]:
        """SDN VNetのサブネット情報を取得"""
        try:
            return self._request('GET', f'/cluster/sdn/vnets/{vnet}/subnets')
        except Exception as e:
            logger.warning(f"SDN subnets not available for {vnet}: {e}")
            return []
