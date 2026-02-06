import React, { useEffect, useRef, useState } from 'react';
import cytoscape from 'cytoscape';
import cola from 'cytoscape-cola';

// colaレイアウトを登録
cytoscape.use(cola);

const TopologyView = ({ topologyData }) => {
  const cyRef = useRef(null);
  const containerRef = useRef(null);
  const [selectedElement, setSelectedElement] = useState(null);

  useEffect(() => {
    if (!topologyData || !containerRef.current) return;

    // Cytoscapeインスタンスを初期化
    const cy = cytoscape({
      container: containerRef.current,
      
      elements: {
        nodes: topologyData.nodes.map(node => ({
          data: {
            id: node.id,
            label: node.label,
            type: node.type,
            ...node
          }
        })),
        edges: topologyData.edges.map(edge => ({
          data: {
            id: `${edge.source}-${edge.target}`,
            source: edge.source,
            target: edge.target,
            label: edge.label || edge.type,
            ...edge
          }
        }))
      },

      style: [
        // 基本スタイル
        {
          selector: 'node',
          style: {
            'label': 'data(label)',
            'text-valign': 'center',
            'text-halign': 'center',
            'font-size': '12px',
            'width': '80px',
            'height': '80px',
            'border-width': '2px',
            'border-color': '#666',
            'background-color': '#fff'
          }
        },
        
        // 物理ノード（Proxmoxサーバー）
        {
          selector: 'node[type="physical_node"]',
          style: {
            'shape': 'round-rectangle',
            'background-color': '#4A90E2',
            'width': '120px',
            'height': '100px',
            'font-weight': 'bold',
            'color': '#fff',
            'text-outline-width': 2,
            'text-outline-color': '#4A90E2'
          }
        },
        
        // VM
        {
          selector: 'node[type="vm"]',
          style: {
            'shape': 'ellipse',
            'background-color': '#7ED321',
            'width': '80px',
            'height': '80px'
          }
        },
        
        // コンテナ
        {
          selector: 'node[type="container"]',
          style: {
            'shape': 'hexagon',
            'background-color': '#F5A623',
            'width': '80px',
            'height': '80px'
          }
        },
        
        // ブリッジネットワーク
        {
          selector: 'node[type="bridge"]',
          style: {
            'shape': 'diamond',
            'background-color': '#BD10E0',
            'width': '100px',
            'height': '100px'
          }
        },
        
        // VLAN
        {
          selector: 'node[type="vlan"]',
          style: {
            'shape': 'triangle',
            'background-color': '#50E3C2',
            'width': '90px',
            'height': '90px'
          }
        },
        
        // SDN VNET
        {
          selector: 'node[type="sdn_vnet"]',
          style: {
            'shape': 'star',
            'background-color': '#FF6B6B',
            'width': '100px',
            'height': '100px'
          }
        },
        
        // エッジ（接続線）
        {
          selector: 'edge',
          style: {
            'width': 3,
            'line-color': '#999',
            'target-arrow-color': '#999',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'label': 'data(label)',
            'font-size': '10px',
            'text-rotation': 'autorotate',
            'text-margin-y': -10
          }
        },
        
        // 物理接続
        {
          selector: 'edge[type="physical_connection"]',
          style: {
            'line-color': '#4A90E2',
            'width': 4,
            'line-style': 'solid'
          }
        },
        
        // ネットワーク接続
        {
          selector: 'edge[type="network_connection"]',
          style: {
            'line-color': '#7ED321',
            'width': 2
          }
        },
        
        // VLAN接続
        {
          selector: 'edge[vlan]',
          style: {
            'line-color': '#50E3C2',
            'line-style': 'dashed',
            'width': 2
          }
        },
        
        // ホスト関係
        {
          selector: 'edge[type="hosts"]',
          style: {
            'line-color': '#ccc',
            'width': 2,
            'line-style': 'dotted',
            'target-arrow-shape': 'none'
          }
        },
        
        // 選択状態
        {
          selector: ':selected',
          style: {
            'border-width': '4px',
            'border-color': '#ff0000',
            'background-color': '#ffcccc'
          }
        }
      ],

      layout: {
        name: 'cola',
        animate: true,
        randomize: false,
        maxSimulationTime: 4000,
        nodeSpacing: 100,
        edgeLength: 200,
        fit: true,
        padding: 50,
        componentSpacing: 150
      },

      wheelSensitivity: 0.2,
      minZoom: 0.1,
      maxZoom: 3
    });

    // クリックイベント
    cy.on('tap', 'node', (event) => {
      const node = event.target;
      setSelectedElement(node.data());
    });

    cy.on('tap', 'edge', (event) => {
      const edge = event.target;
      setSelectedElement(edge.data());
    });

    // 背景クリックで選択解除
    cy.on('tap', (event) => {
      if (event.target === cy) {
        setSelectedElement(null);
        cy.$(':selected').unselect();
      }
    });

    cyRef.current = cy;

    // クリーンアップ
    return () => {
      if (cyRef.current) {
        cyRef.current.destroy();
      }
    };
  }, [topologyData]);

  return (
    <div style={{ display: 'flex', height: '100vh', width: '100%' }}>
      <div
        ref={containerRef}
        style={{
          flex: 1,
          backgroundColor: '#f5f5f5',
          border: '1px solid #ddd'
        }}
      />
      
      {selectedElement && (
        <div style={{
          width: '350px',
          padding: '20px',
          backgroundColor: '#fff',
          borderLeft: '1px solid #ddd',
          overflowY: 'auto'
        }}>
          <h3 style={{ marginTop: 0, borderBottom: '2px solid #4A90E2', paddingBottom: '10px' }}>
            {selectedElement.label || selectedElement.id}
          </h3>
          
          <div style={{ fontSize: '14px' }}>
            <p><strong>Type:</strong> {selectedElement.type}</p>
            
            {selectedElement.status && (
              <p><strong>Status:</strong> 
                <span style={{
                  color: selectedElement.status === 'running' || selectedElement.status === 'online' ? 'green' : 'red',
                  marginLeft: '5px'
                }}>
                  {selectedElement.status}
                </span>
              </p>
            )}
            
            {selectedElement.vmid && (
              <p><strong>VM ID:</strong> {selectedElement.vmid}</p>
            )}
            
            {selectedElement.node && (
              <p><strong>Host Node:</strong> {selectedElement.node}</p>
            )}
            
            {selectedElement.cpu && (
              <p><strong>CPU:</strong> {selectedElement.cpu}</p>
            )}
            
            {selectedElement.mem && (
              <p><strong>Memory:</strong> {(selectedElement.mem / 1024 / 1024 / 1024).toFixed(2)} GB</p>
            )}
            
            {selectedElement.vlan && (
              <p><strong>VLAN:</strong> {selectedElement.vlan}</p>
            )}
            
            {selectedElement.vlan_id && (
              <p><strong>VLAN ID:</strong> {selectedElement.vlan_id}</p>
            )}
            
            {selectedElement.cidr && (
              <p><strong>CIDR:</strong> {selectedElement.cidr}</p>
            )}
            
            {selectedElement.gateway && (
              <p><strong>Gateway:</strong> {selectedElement.gateway}</p>
            )}
            
            {selectedElement.ips && selectedElement.ips.length > 0 && (
              <div>
                <p><strong>IP Addresses:</strong></p>
                <ul style={{ marginTop: '5px', paddingLeft: '20px' }}>
                  {selectedElement.ips.map((ip, idx) => (
                    <li key={idx}>{ip}</li>
                  ))}
                </ul>
              </div>
            )}
            
            {selectedElement.mac && (
              <p><strong>MAC:</strong> {selectedElement.mac}</p>
            )}
            
            {selectedElement.interface && (
              <p><strong>Interface:</strong> {selectedElement.interface}</p>
            )}
            
            {selectedElement.bridge_vlan_aware && (
              <p><strong>VLAN Aware:</strong> {selectedElement.bridge_vlan_aware ? 'Yes' : 'No'}</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default TopologyView;
