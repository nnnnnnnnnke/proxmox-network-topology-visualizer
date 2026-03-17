from typing import Dict, List
import re
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

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
        ips = []
        for key, value in config.items():
            if key.startswith('ipconfig'):
                if isinstance(value, str) and 'ip=' in value:
                    match = re.search(r'ip=([0-9\.]+/[0-9]+)', value)
                    if match:
                        ips.append(match.group(1))
        return ips

    def extract_ip_from_lxc_config(self, config: Dict) -> List[str]:
        ips = []
        for key, value in config.items():
            if key.startswith('net') and isinstance(value, str):
                match = re.search(r'ip=([0-9\.]+/[0-9]+)', value)
                if match:
                    ips.append(match.group(1))
        return ips

    def extract_agent_ips(self, interfaces: list) -> List[str]:
        ips = []
        for iface in interfaces:
            if iface.get('name') == 'lo':
                continue
            for addr in iface.get('ip-addresses', []):
                ip = addr.get('ip-address', '')
                prefix = addr.get('prefix', '')
                if addr.get('ip-address-type') == 'ipv4' and ip:
                    ips.append(f"{ip}/{prefix}" if prefix else ip)
        return ips

    def _fetch_metadata(self):
        """メタデータを並列取得"""
        results = {}
        with ThreadPoolExecutor(max_workers=6) as ex:
            futs = {
                ex.submit(self.client.get_cluster_status): 'cluster_status',
                ex.submit(self.client.get_sdn_vnets): 'sdn_vnets',
                ex.submit(self.client.get_sdn_zones): 'sdn_zones',
                ex.submit(self.client.get_nodes): 'nodes',
            }
            for f in as_completed(futs):
                key = futs[f]
                try:
                    results[key] = f.result()
                except Exception as e:
                    logger.error(f"Failed to fetch {key}: {e}")
                    results[key] = [] if key != 'cluster_status' else {}
        return results

    def _fetch_node_data(self, node_name: str):
        """ノードのネットワーク設定とVM一覧を並列取得"""
        results = {}
        with ThreadPoolExecutor(max_workers=2) as ex:
            futs = {
                ex.submit(self.client.get_node_network, node_name): 'network',
                ex.submit(self.client.get_vms, node_name): 'vms',
            }
            for f in as_completed(futs):
                key = futs[f]
                try:
                    results[key] = f.result()
                except Exception as e:
                    logger.error(f"Failed to fetch {key} for {node_name}: {e}")
                    results[key] = []
        return results

    def _fetch_vm_configs_parallel(self, node_name: str, vms: list) -> Dict[int, Dict]:
        """全VMのconfigを並列取得"""
        configs = {}
        with ThreadPoolExecutor(max_workers=10) as ex:
            futs = {}
            for vm in vms:
                vmid = vm['vmid']
                vm_type = vm.get('type', 'qemu')
                futs[ex.submit(self.client.get_vm_config, node_name, vmid, vm_type)] = vmid
            for f in as_completed(futs):
                vmid = futs[f]
                try:
                    configs[vmid] = f.result()
                except Exception:
                    configs[vmid] = {}
        return configs

    def analyze_topology(self, hide_stopped=True, hide_hosts_edges=True,
                         hide_physical_node=True, skip_agent=False) -> Dict:
        nodes = []
        edges = []
        networks = {}
        vlans = {}
        running_count = 0
        stopped_count = 0
        total_vm_count = 0

        # Phase 1: メタデータ並列取得
        meta = self._fetch_metadata()

        cluster_status = meta['cluster_status']
        try:
            cluster_name = next(
                (item['name'] for item in cluster_status if item['type'] == 'cluster'),
                'proxmox-cluster'
            )
        except Exception:
            cluster_name = 'proxmox-cluster'

        sdn_vnets = meta['sdn_vnets']
        sdn_bridge_names = {vnet['vnet'] for vnet in sdn_vnets}

        sdn_zones = {}
        for zone in meta['sdn_zones']:
            sdn_zones[zone.get('zone', '')] = zone

        # SDN Subnet並列取得
        sdn_subnets = {}
        if sdn_vnets:
            with ThreadPoolExecutor(max_workers=5) as ex:
                futs = {ex.submit(self.client.get_sdn_subnets, v['vnet']): v['vnet'] for v in sdn_vnets}
                for f in as_completed(futs):
                    vn = futs[f]
                    try:
                        result = f.result()
                        if result:
                            sdn_subnets[vn] = result
                    except Exception:
                        pass

        pve_nodes = meta['nodes']

        # Phase 2: 各ノードのデータ取得 & VM config並列取得
        all_vms_data = []
        agent_tasks = []

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

            node_data = self._fetch_node_data(node_name)
            network_configs = node_data['network']
            vms = node_data['vms']

            # ネットワーク設定を処理
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

            # 表示対象VMをフィルタ
            visible_vms = []
            for vm in vms:
                vm_status = vm.get('status', 'unknown')
                total_vm_count += 1
                if vm_status == 'running':
                    running_count += 1
                else:
                    stopped_count += 1
                if hide_stopped and vm_status != 'running':
                    continue
                visible_vms.append(vm)

            # VM config並列取得
            configs = self._fetch_vm_configs_parallel(node_name, visible_vms)

            for vm in visible_vms:
                vmid = vm['vmid']
                config = configs.get(vmid, {})
                vm_type = vm.get('type', 'qemu')

                all_vms_data.append((node_name, vm, config, vm_type))

                # Guest Agent対象を収集
                if (not skip_agent and vm_type == 'qemu'
                        and vm.get('status') == 'running'
                        and config.get('agent', '0').split(',')[0] == '1'):
                    agent_tasks.append((node_name, vmid))

        # Phase 3: Guest Agent並列取得
        agent_results = {}
        if agent_tasks:
            agent_results = self.client.get_vm_agent_interfaces_batch(agent_tasks)

        # Phase 4: ノード・エッジ構築
        for node_name, vm, config, vm_type in all_vms_data:
            vmid = vm['vmid']
            vm_name = vm.get('name', f'VM-{vmid}')
            vm_status = vm.get('status', 'unknown')
            vm_id = f"vm-{node_name}-{vmid}"
            node_id = f"node-{node_name}"

            # IP取得
            ips = []
            if vmid in agent_results and agent_results[vmid]:
                ips = self.extract_agent_ips(agent_results[vmid])
            if not ips:
                if vm_type == 'qemu':
                    ips = self.extract_ip_from_config(config)
                else:
                    ips = self.extract_ip_from_lxc_config(config)

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
                                edges.append({
                                    'source': f"vlan-{bridge}-{vlan_tag}",
                                    'target': target_net,
                                    'type': 'vlan_connection',
                                    'interface': f"VLAN {vlan_tag}",
                                })

                            edge_data = {
                                'source': vm_id,
                                'target': f"vlan-{bridge}-{vlan_tag}",
                                'type': 'network_connection',
                                'interface': key,
                                'mac': net_info.get('mac', ''),
                                'vlan': vlan_tag,
                            }
                        else:
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

        # ネットワーク・VLANノードを追加
        for net_id, net_info in networks.items():
            nodes.append(net_info)
        for vlan_key, vlan_info in vlans.items():
            nodes.append(vlan_info)

        for vnet in sdn_vnets:
            vnet_name = vnet['vnet']
            zone_name = vnet.get('zone', '')
            zone_info = sdn_zones.get(zone_name, {})
            subnets = sdn_subnets.get(vnet_name, [])
            subnet_cidrs = [s.get('cidr', '') for s in subnets if s.get('cidr')]
            subnet_gateways = [s.get('gateway', '') for s in subnets if s.get('gateway')]
            snat_enabled = any(s.get('snat', 0) for s in subnets)

            nodes.append({
                'id': f"sdn-{vnet_name}",
                'label': vnet_name,
                'type': 'sdn_vnet',
                'zone': zone_name,
                'zone_type': zone_info.get('type', ''),
                'tag': vnet.get('tag', ''),
                'cidr': ', '.join(subnet_cidrs) if subnet_cidrs else '',
                'gateway': ', '.join(subnet_gateways) if subnet_gateways else '',
                'snat': snat_enabled,
            })

        # 孤立ネットワーク除去
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
