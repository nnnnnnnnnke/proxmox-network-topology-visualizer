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
                result[key.strip()] = value.strip()
            else:
                if ':' in part and len(part.split(':')) == 6:
                    result['mac'] = part
        return result

    def extract_ip_from_config(self, config: Dict) -> List[str]:
        """cloud-init ipconfig からIPを抽出"""
        ips = []
        for key, value in config.items():
            if key.startswith('ipconfig'):
                if isinstance(value, str) and 'ip=' in value:
                    match = re.search(r'ip=([0-9\.]+/[0-9]+)', value)
                    if match:
                        ips.append(match.group(1))
        return ips

    def extract_ip_from_lxc_config(self, config: Dict) -> List[str]:
        """LXCコンテナのnet設定からIPを抽出"""
        ips = []
        for key, value in config.items():
            if key.startswith('net') and isinstance(value, str):
                match = re.search(r'ip=([0-9\.]+/[0-9]+)', value)
                if match:
                    ips.append(match.group(1))
        return ips

    def get_guest_agent_ips(self, node_name: str, vmid: int) -> List[str]:
        """QEMU Guest Agent経由で実際のIPアドレスを取得"""
        ips = []
        try:
            interfaces = self.client.get_vm_agent_interfaces(node_name, vmid)
            for iface in interfaces:
                if iface.get('name') == 'lo':
                    continue
                for addr in iface.get('ip-addresses', []):
                    ip = addr.get('ip-address', '')
                    prefix = addr.get('prefix', '')
                    if addr.get('ip-address-type') == 'ipv4' and ip:
                        ips.append(f"{ip}/{prefix}" if prefix else ip)
        except Exception:
            pass
        return ips

    def analyze_topology(self, hide_stopped=True, hide_hosts_edges=True,
                         hide_physical_node=True) -> Dict:
        nodes = []
        edges = []
        networks = {}
        vlans = {}
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

        # SDN Zone情報を取得
        sdn_zones = {}
        for zone in self.client.get_sdn_zones():
            sdn_zones[zone.get('zone', '')] = zone

        # SDN Subnet情報を取得
        sdn_subnets = {}
        for vnet in sdn_vnets:
            vnet_name = vnet['vnet']
            subnets = self.client.get_sdn_subnets(vnet_name)
            if subnets:
                sdn_subnets[vnet_name] = subnets

        # Proxmoxノードを取得
        pve_nodes = self.client.get_nodes()

        for pve_node in pve_nodes:
            node_name = pve_node['node']
            node_id = f"node-{node_name}"

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

                    if hide_stopped and vm_status != 'running':
                        continue

                    # IP取得: Guest Agent → cloud-init → LXC config の順でフォールバック
                    ips = []
                    if vm_type == 'qemu' and vm_status == 'running':
                        ips = self.get_guest_agent_ips(node_name, vmid)

                    nodes.append({
                        'id': vm_id,
                        'label': vm_name,
                        'type': 'vm' if vm_type == 'qemu' else 'container',
                        'vmid': vmid,
                        'status': vm_status,
                        'node': node_name,
                        'cpu': vm.get('maxcpu', 0),
                        'mem': vm.get('maxmem', 0),
                        'ips': ips
                    })

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

                        # cloud-init / LXC config からのIP（Guest Agentで取れなかった場合のフォールバック）
                        if not ips:
                            if vm_type == 'qemu':
                                ips = self.extract_ip_from_config(config)
                            else:
                                ips = self.extract_ip_from_lxc_config(config)
                            # ノードデータにIPを反映
                            if ips:
                                for n in nodes:
                                    if n['id'] == vm_id:
                                        n['ips'] = ips
                                        break

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

                                    # VLANタグがある場合、VLANノードを経由
                                    if vlan_tag:
                                        vlan_key = f"{bridge}-vlan-{vlan_tag}"
                                        if vlan_key not in vlans:
                                            vlans[vlan_key] = {
                                                'id': f"vlan-{bridge}-{vlan_tag}",
                                                'label': f"VLAN {vlan_tag}",
                                                'type': 'vlan',
                                                'vlan_id': vlan_tag,
                                                'parent_bridge': bridge
                                            }
                                            # VLANノード → ブリッジへのエッジ
                                            edges.append({
                                                'source': f"vlan-{bridge}-{vlan_tag}",
                                                'target': target_net,
                                                'type': 'vlan_connection',
                                                'interface': f"VLAN {vlan_tag}",
                                            })

                                        # VM → VLANノードへのエッジ
                                        edge_data = {
                                            'source': vm_id,
                                            'target': f"vlan-{bridge}-{vlan_tag}",
                                            'type': 'network_connection',
                                            'interface': key,
                                            'mac': net_info.get('mac', ''),
                                            'vlan': vlan_tag,
                                        }
                                    else:
                                        # VLANなし → 直接ブリッジへ
                                        edge_data = {
                                            'source': vm_id,
                                            'target': target_net,
                                            'type': 'network_connection',
                                            'interface': key,
                                            'mac': net_info.get('mac', ''),
                                        }

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

        # VLANノードを追加
        for vlan_key, vlan_info in vlans.items():
            nodes.append(vlan_info)

        # SDN VNetノードを追加（Zone・Subnet情報付き）
        for vnet in sdn_vnets:
            vnet_name = vnet['vnet']
            vnet_id = f"sdn-{vnet_name}"
            zone_name = vnet.get('zone', '')
            zone_info = sdn_zones.get(zone_name, {})
            subnets = sdn_subnets.get(vnet_name, [])

            subnet_cidrs = [s.get('cidr', '') for s in subnets if s.get('cidr')]
            subnet_gateways = [s.get('gateway', '') for s in subnets if s.get('gateway')]
            snat_enabled = any(s.get('snat', 0) for s in subnets)

            nodes.append({
                'id': vnet_id,
                'label': vnet_name,
                'type': 'sdn_vnet',
                'zone': zone_name,
                'zone_type': zone_info.get('type', ''),
                'tag': vnet.get('tag', ''),
                'cidr': ', '.join(subnet_cidrs) if subnet_cidrs else '',
                'gateway': ', '.join(subnet_gateways) if subnet_gateways else '',
                'snat': snat_enabled,
            })

        # 接続VMがないネットワークを除去
        connected_targets = set()
        for e in edges:
            if e['type'] in ('network_connection', 'vlan_connection'):
                connected_targets.add(e['target'])
                connected_targets.add(e['source'])
        if not hide_physical_node:
            connected_targets |= {e['target'] for e in edges if e['type'] == 'physical_connection'}

        removable_types = ('bridge', 'sdn_vnet', 'vlan')
        nodes = [n for n in nodes
                 if n.get('type') not in removable_types
                 or n['id'] in connected_targets]

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
                'total_vlans': len(vlans),
                'total_sdn': len(sdn_vnets),
                'filters': {
                    'hide_stopped': hide_stopped,
                    'hide_hosts_edges': hide_hosts_edges,
                    'hide_physical_node': hide_physical_node
                }
            }
        }
