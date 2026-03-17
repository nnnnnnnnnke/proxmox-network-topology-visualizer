from typing import Dict, List, Set
import re
import logging

logger = logging.getLogger(__name__)


class TopologyAnalyzer:
    """ネットワークトポロジを解析してグラフデータを生成"""

    def __init__(self, proxmox_client):
        self.client = proxmox_client

    def parse_network_config(self, config_str: str) -> Dict:
        parts = config_str.split(',')
        result = {}
        for part in parts:
            if '=' in part:
                key, value = part.split('=', 1)
                result[key] = value
            else:
                if ':' in part and len(part.split(':')) == 6:
                    result['mac'] = part
        return result

    def extract_ip_from_config(self, config: Dict) -> List[str]:
        ips = []
        for key, value in config.items():
            if key.startswith('ipconfig'):
                if isinstance(value, str) and 'ip=' in value:
                    match = re.search(r'ip=([0-9\.]+/[0-9]+)', value)
                    if match:
                        ips.append(match.group(1))
        return ips

    def analyze_topology(self, hide_stopped=True, hide_hosts_edges=True,
                         hide_physical_node=True) -> Dict:
        nodes = []
        edges = []
        networks = {}
        skipped_vm_ids = set()
        running_count = 0
        stopped_count = 0
        total_vm_count = 0

        # クラスタ情報
        try:
            cluster_status = self.client.get_cluster_status()
            cluster_name = next(
                (item['name'] for item in cluster_status if item['type'] == 'cluster'),
                'proxmox-cluster'
            )
        except Exception:
            cluster_name = 'proxmox-cluster'

        # SDN情報を先に取得
        sdn_vnets = self.client.get_sdn_vnets()
        sdn_bridge_names = {vnet['vnet'] for vnet in sdn_vnets}

        # Proxmoxノードを取得
        pve_nodes = self.client.get_nodes()

        for pve_node in pve_nodes:
            node_name = pve_node['node']
            node_id = f"node-{node_name}"

            # 物理ノード（フィルタ対応）
            if not hide_physical_node:
                nodes.append({
                    'id': node_id,
                    'label': node_name,
                    'type': 'physical_node',
                    'status': pve_node.get('status', 'unknown'),
                    'cpu': pve_node.get('maxcpu', 0),
                    'mem': pve_node.get('maxmem', 0),
                    'uptime': pve_node.get('uptime', 0)
                })

            # ネットワーク設定を取得
            try:
                network_configs = self.client.get_node_network(node_name)
                for net_config in network_configs:
                    iface_name = net_config.get('iface', '')
                    net_type = net_config.get('type', '')

                    if net_type == 'bridge':
                        if iface_name not in networks:
                            networks[iface_name] = {
                                'id': f"network-{iface_name}",
                                'label': iface_name,
                                'type': 'bridge',
                                'vlan_aware': net_config.get('bridge_vlan_aware', 0),
                                'cidr': net_config.get('cidr', ''),
                                'gateway': net_config.get('gateway', ''),
                                'nodes': []
                            }
                        networks[iface_name]['nodes'].append(node_name)

                        if not hide_physical_node:
                            edges.append({
                                'source': node_id,
                                'target': f"network-{iface_name}",
                                'type': 'physical_connection',
                                'interface': iface_name,
                                'cidr': net_config.get('cidr', ''),
                                'gateway': net_config.get('gateway', '')
                            })

                    elif '.' in iface_name:
                        parent_iface, vlan_id = iface_name.rsplit('.', 1)
                        vlan_net_id = f"vlan-{vlan_id}"
                        if vlan_net_id not in networks:
                            networks[vlan_net_id] = {
                                'id': vlan_net_id,
                                'label': f"VLAN {vlan_id}",
                                'type': 'vlan',
                                'vlan_id': vlan_id,
                                'nodes': []
                            }
                        networks[vlan_net_id]['nodes'].append(node_name)

            except Exception as e:
                logger.error(f"Failed to get network config for node {node_name}: {e}")

            # VM/コンテナを取得
            try:
                vms = self.client.get_vms(node_name)
                for vm in vms:
                    vmid = vm['vmid']
                    vm_name = vm.get('name', f'VM-{vmid}')
                    vm_type = vm.get('type', 'qemu')
                    vm_status = vm.get('status', 'unknown')
                    vm_id = f"vm-{node_name}-{vmid}"
                    total_vm_count += 1

                    if vm_status == 'running':
                        running_count += 1
                    else:
                        stopped_count += 1

                    # 停止VMフィルタ
                    if hide_stopped and vm_status != 'running':
                        skipped_vm_ids.add(vm_id)
                        continue

                    nodes.append({
                        'id': vm_id,
                        'label': vm_name,
                        'type': 'vm' if vm_type == 'qemu' else 'container',
                        'vmid': vmid,
                        'status': vm_status,
                        'node': node_name,
                        'cpu': vm.get('maxcpu', 0),
                        'mem': vm.get('maxmem', 0)
                    })

                    # hostsエッジ（フィルタ対応）
                    if not hide_hosts_edges and not hide_physical_node:
                        edges.append({
                            'source': node_id,
                            'target': vm_id,
                            'type': 'hosts',
                            'label': 'hosts'
                        })

                    # VMのネットワーク設定
                    try:
                        config = self.client.get_vm_config(node_name, vmid, vm_type)
                        ips = self.extract_ip_from_config(config)

                        for key, value in config.items():
                            if key.startswith('net') and isinstance(value, str):
                                net_info = self.parse_network_config(value)
                                bridge = net_info.get('bridge', '')
                                vlan_tag = net_info.get('tag', '')

                                if bridge:
                                    if bridge in sdn_bridge_names:
                                        target_net = f"sdn-{bridge}"
                                    else:
                                        target_net = f"network-{bridge}"

                                    edge_data = {
                                        'source': vm_id,
                                        'target': target_net,
                                        'type': 'network_connection',
                                        'interface': key,
                                        'mac': net_info.get('mac', ''),
                                        'model': net_info.get('virtio', net_info.get('e1000', '')),
                                    }
                                    if vlan_tag:
                                        edge_data['vlan'] = vlan_tag
                                        edge_data['label'] = f"VLAN {vlan_tag}"
                                    if ips:
                                        edge_data['ips'] = ips
                                    edges.append(edge_data)

                    except Exception as e:
                        logger.warning(f"Failed to get VM config for {vmid}: {e}")

            except Exception as e:
                logger.error(f"Failed to get VMs for node {node_name}: {e}")

        # ネットワークノードを追加
        for net_id, net_info in networks.items():
            nodes.append(net_info)

        # SDN VNetノードを追加
        for vnet in sdn_vnets:
            vnet_id = f"sdn-{vnet['vnet']}"
            nodes.append({
                'id': vnet_id,
                'label': vnet['vnet'],
                'type': 'sdn_vnet',
                'zone': vnet.get('zone', ''),
                'tag': vnet.get('tag', '')
            })

        # 接続VMがないネットワークを除去
        connected_networks = {e['target'] for e in edges if e['type'] == 'network_connection'}
        # 物理ノード表示時はphysical_connectionのtargetも残す
        if not hide_physical_node:
            connected_networks |= {e['target'] for e in edges if e['type'] == 'physical_connection'}
        nodes = [n for n in nodes
                 if n.get('type') not in ('bridge', 'sdn_vnet', 'vlan')
                 or n['id'] in connected_networks]
        # 孤立ネットワークへのエッジも除去
        valid_node_ids = {n['id'] for n in nodes}
        edges = [e for e in edges
                 if e['source'] in valid_node_ids and e['target'] in valid_node_ids]

        return {
            'nodes': nodes,
            'edges': edges,
            'cluster_name': cluster_name,
            'summary': {
                'total_nodes': len(pve_nodes),
                'total_vms': total_vm_count,
                'running_vms': running_count,
                'stopped_vms': stopped_count,
                'total_networks': len(networks),
                'total_sdn': len(sdn_vnets),
                'filters': {
                    'hide_stopped': hide_stopped,
                    'hide_hosts_edges': hide_hosts_edges,
                    'hide_physical_node': hide_physical_node
                }
            }
        }
