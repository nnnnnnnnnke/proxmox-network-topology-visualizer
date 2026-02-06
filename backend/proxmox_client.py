import requests
import urllib3
from typing import Dict, List, Optional
import logging

# 自己署名証明書の警告を無効化（本番環境では適切な証明書を使用してください）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProxmoxClient:
    """Proxmox VE API クライアント"""
    
    def __init__(self, host: str, token_id: str, token_secret: str, verify_ssl: bool = False):
        """
        Args:
            host: Proxmox ホスト (例: 'https://192.168.1.100:8006')
            token_id: API トークンID (例: 'user@pam!tokenname')
            token_secret: API トークンシークレット
            verify_ssl: SSL証明書を検証するか
        """
        self.host = host.rstrip('/')
        self.verify_ssl = verify_ssl
        self.headers = {
            'Authorization': f'PVEAPIToken={token_id}={token_secret}'
        }
        
    def _request(self, method: str, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """APIリクエストを実行"""
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
        """クラスタ内の全ノード情報を取得"""
        return self._request('GET', '/cluster/resources', {'type': 'node'})
    
    def get_node_network(self, node: str) -> List[Dict]:
        """指定ノードのネットワーク設定を取得"""
        return self._request('GET', f'/nodes/{node}/network')
    
    def get_vms(self, node: str) -> List[Dict]:
        """指定ノードの全VM情報を取得"""
        qemu_vms = self._request('GET', f'/nodes/{node}/qemu')
        lxc_containers = self._request('GET', f'/nodes/{node}/lxc')
        return qemu_vms + lxc_containers
    
    def get_vm_config(self, node: str, vmid: int, vm_type: str = 'qemu') -> Dict:
        """VM/コンテナの詳細設定を取得"""
        return self._request('GET', f'/nodes/{node}/{vm_type}/{vmid}/config')
    
    def get_vm_interfaces(self, node: str, vmid: int, vm_type: str = 'qemu') -> List[Dict]:
        """VM/コンテナのネットワークインターフェース情報を取得"""
        config = self.get_vm_config(node, vmid, vm_type)
        interfaces = []
        
        for key, value in config.items():
            if key.startswith('net'):
                interfaces.append({
                    'interface': key,
                    'config': value,
                    'vmid': vmid
                })
        
        return interfaces
    
    def get_cluster_status(self) -> Dict:
        """クラスタステータスを取得"""
        return self._request('GET', '/cluster/status')
    
    def get_sdn_vnets(self) -> List[Dict]:
        """SDN VNETの情報を取得"""
        try:
            return self._request('GET', '/cluster/sdn/vnets')
        except Exception as e:
            logger.warning(f"SDN not available or configured: {e}")
            return []
    
    def get_sdn_zones(self) -> List[Dict]:
        """SDN Zoneの情報を取得"""
        try:
            return self._request('GET', '/cluster/sdn/zones')
        except Exception as e:
            logger.warning(f"SDN zones not available: {e}")
            return []
