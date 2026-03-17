import React, { useEffect, useRef, useState } from 'react';
import cytoscape from 'cytoscape';

const computeLayout = (nodes, edges) => {
  const hubs = nodes.filter(n => n.type === 'bridge' || n.type === 'sdn_vnet');
  const physNode = nodes.find(n => n.type === 'physical_node');

  // Group VMs by their connected hub
  const hubVMs = {};
  hubs.forEach(h => { hubVMs[h.id] = []; });
  edges.forEach(e => {
    if (e.type === 'network_connection' && hubVMs[e.target]) {
      const vm = nodes.find(n => n.id === e.source);
      if (vm) hubVMs[e.target].push(vm);
    }
  });

  const positions = {};
  const hubSpacing = 350;
  const startX = -(hubs.length - 1) * hubSpacing / 2;

  hubs.forEach((hub, i) => {
    const cx = startX + i * hubSpacing;
    const cy = 0;
    positions[hub.id] = { x: cx, y: cy };

    const vms = hubVMs[hub.id] || [];
    if (vms.length === 0) return;

    const radius = Math.max(140, vms.length * 45);
    vms.forEach((vm, j) => {
      // Spread VMs in a semicircle below the hub
      const angleStart = Math.PI * 0.15;
      const angleEnd = Math.PI * 0.85;
      const angle = vms.length === 1
        ? Math.PI * 0.5
        : angleStart + (angleEnd - angleStart) * j / (vms.length - 1);
      positions[vm.id] = {
        x: cx + radius * Math.cos(angle),
        y: cy + radius * Math.sin(angle)
      };
    });
  });

  // Physical node at top center
  if (physNode) {
    positions[physNode.id] = { x: 0, y: -250 };
  }

  // Any unpositioned nodes
  nodes.forEach((n, i) => {
    if (!positions[n.id]) {
      positions[n.id] = { x: -300 + i * 60, y: 300 };
    }
  });

  return positions;
};

const TopologyView = ({ topologyData }) => {
  const cyRef = useRef(null);
  const containerRef = useRef(null);
  const [selectedElement, setSelectedElement] = useState(null);

  useEffect(() => {
    if (!topologyData || !containerRef.current) return;

    const positions = computeLayout(topologyData.nodes, topologyData.edges);

    const cy = cytoscape({
      container: containerRef.current,

      elements: {
        nodes: topologyData.nodes.map(node => ({
          data: { id: node.id, label: node.label, type: node.type, ...node }
        })),
        edges: topologyData.edges.map(edge => ({
          data: {
            id: `${edge.source}-${edge.target}`,
            source: edge.source,
            target: edge.target,
            type: edge.type,
            ...edge
          }
        }))
      },

      style: [
        // Base node
        {
          selector: 'node',
          style: {
            'label': 'data(label)',
            'text-valign': 'bottom',
            'text-halign': 'center',
            'text-margin-y': 8,
            'font-size': '11px',
            'font-family': '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
            'width': '50px',
            'height': '50px',
            'border-width': '2px',
            'border-color': '#ddd',
            'background-color': '#fff',
            'text-max-width': '100px',
            'text-wrap': 'ellipsis',
            'color': '#374151'
          }
        },
        // Bridge
        {
          selector: 'node[type="bridge"]',
          style: {
            'shape': 'round-rectangle',
            'background-color': '#6366F1',
            'width': '100px',
            'height': '55px',
            'color': '#fff',
            'text-valign': 'center',
            'text-margin-y': 0,
            'font-size': '14px',
            'font-weight': 'bold',
            'text-outline-width': 2,
            'text-outline-color': '#6366F1',
            'border-width': 0
          }
        },
        // SDN VNet
        {
          selector: 'node[type="sdn_vnet"]',
          style: {
            'shape': 'round-rectangle',
            'background-color': '#EC4899',
            'width': '100px',
            'height': '55px',
            'color': '#fff',
            'text-valign': 'center',
            'text-margin-y': 0,
            'font-size': '14px',
            'font-weight': 'bold',
            'text-outline-width': 2,
            'text-outline-color': '#EC4899',
            'border-width': 0
          }
        },
        // Running VM
        {
          selector: 'node[type="vm"][status="running"]',
          style: {
            'shape': 'ellipse',
            'background-color': '#10B981',
            'border-color': '#059669',
            'border-width': '2px',
            'width': '55px',
            'height': '55px',
            'color': '#1F2937',
            'font-weight': '500'
          }
        },
        // Stopped VM
        {
          selector: 'node[type="vm"][status="stopped"]',
          style: {
            'shape': 'ellipse',
            'background-color': '#E5E7EB',
            'border-color': '#D1D5DB',
            'border-width': '1px',
            'width': '40px',
            'height': '40px',
            'color': '#9CA3AF',
            'font-size': '9px',
            'opacity': 0.6
          }
        },
        // Container
        {
          selector: 'node[type="container"]',
          style: {
            'shape': 'hexagon',
            'background-color': '#F59E0B',
            'border-color': '#D97706',
            'border-width': '2px',
            'width': '55px',
            'height': '55px'
          }
        },
        // Physical node
        {
          selector: 'node[type="physical_node"]',
          style: {
            'shape': 'round-rectangle',
            'background-color': '#3B82F6',
            'width': '120px',
            'height': '50px',
            'font-weight': 'bold',
            'color': '#fff',
            'text-valign': 'center',
            'text-margin-y': 0,
            'text-outline-width': 2,
            'text-outline-color': '#3B82F6',
            'border-width': 0
          }
        },
        // Edge base
        {
          selector: 'edge',
          style: {
            'width': 1.5,
            'line-color': '#CBD5E1',
            'curve-style': 'bezier',
            'target-arrow-shape': 'none',
            'opacity': 0.6
          }
        },
        // Network connection
        {
          selector: 'edge[type="network_connection"]',
          style: {
            'line-color': '#94A3B8',
            'width': 1.5
          }
        },
        // Physical connection
        {
          selector: 'edge[type="physical_connection"]',
          style: {
            'line-color': '#3B82F6',
            'width': 3
          }
        },
        // Hosts edge
        {
          selector: 'edge[type="hosts"]',
          style: {
            'line-color': '#E2E8F0',
            'width': 1,
            'line-style': 'dotted',
            'opacity': 0.4
          }
        },
        // Selected
        {
          selector: ':selected',
          style: {
            'border-width': '3px',
            'border-color': '#F59E0B',
            'overlay-color': '#F59E0B',
            'overlay-padding': 6,
            'overlay-opacity': 0.1
          }
        },
        // Highlight classes
        {
          selector: '.highlighted',
          style: {
            'opacity': 1,
            'border-width': '3px',
            'border-color': '#F59E0B'
          }
        },
        {
          selector: '.dimmed',
          style: { 'opacity': 0.12 }
        },
        {
          selector: 'edge.highlighted',
          style: {
            'opacity': 1,
            'width': 3,
            'line-color': '#F59E0B'
          }
        }
      ],

      layout: {
        name: 'preset',
        positions: (node) => positions[node.id()] || { x: 0, y: 0 },
        fit: true,
        padding: 80
      },

      minZoom: 0.3,
      maxZoom: 3
    });

    // Click: highlight neighbors
    cy.on('tap', 'node', (event) => {
      const node = event.target;
      setSelectedElement(node.data());
      cy.elements().addClass('dimmed');
      node.removeClass('dimmed').addClass('highlighted');
      node.connectedEdges().removeClass('dimmed').addClass('highlighted');
      node.neighborhood().nodes().removeClass('dimmed').addClass('highlighted');
    });

    cy.on('tap', 'edge', (event) => {
      const edge = event.target;
      setSelectedElement(edge.data());
      cy.elements().addClass('dimmed');
      edge.removeClass('dimmed').addClass('highlighted');
      edge.source().removeClass('dimmed').addClass('highlighted');
      edge.target().removeClass('dimmed').addClass('highlighted');
    });

    cy.on('tap', (event) => {
      if (event.target === cy) {
        setSelectedElement(null);
        cy.elements().removeClass('dimmed highlighted');
      }
    });

    cyRef.current = cy;
    return () => { if (cyRef.current) cyRef.current.destroy(); };
  }, [topologyData]);

  return (
    <div style={{ position: 'relative', height: '100%', width: '100%' }}>
      <div
        ref={containerRef}
        style={{ width: '100%', height: '100%', backgroundColor: '#F8FAFC' }}
      />

      {/* Inline legend */}
      <div style={{
        position: 'absolute', bottom: 16, left: 16,
        background: 'rgba(255,255,255,0.92)', borderRadius: 10,
        padding: '10px 16px', fontSize: 12, boxShadow: '0 2px 12px rgba(0,0,0,0.08)',
        display: 'flex', gap: 16, alignItems: 'center', flexWrap: 'wrap'
      }}>
        <LegendDot color="#10B981" label="Running VM" />
        <LegendDot color="#E5E7EB" label="Stopped VM" />
        <LegendRect color="#6366F1" label="Bridge" />
        <LegendRect color="#EC4899" label="SDN VNet" />
        <LegendRect color="#3B82F6" label="Physical Node" />
      </div>

      {/* Detail panel */}
      {selectedElement && (
        <div style={{
          position: 'absolute', top: 16, right: 16, width: 300,
          maxHeight: 'calc(100% - 32px)',
          padding: '20px', backgroundColor: 'rgba(255,255,255,0.95)',
          borderRadius: 12, boxShadow: '0 4px 24px rgba(0,0,0,0.12)',
          overflowY: 'auto', backdropFilter: 'blur(8px)'
        }}>
          <button
            onClick={() => {
              setSelectedElement(null);
              cyRef.current?.elements().removeClass('dimmed highlighted');
            }}
            style={{
              position: 'absolute', top: 8, right: 12, border: 'none',
              background: 'none', fontSize: 18, cursor: 'pointer', color: '#9CA3AF'
            }}
          >
            &times;
          </button>

          <h3 style={{ margin: '0 0 12px', fontSize: 16, color: '#1F2937' }}>
            {selectedElement.label || selectedElement.id}
          </h3>

          <div style={{ fontSize: 14, lineHeight: 1.8 }}>
            <DetailRow label="Type" value={selectedElement.type} />
            {selectedElement.status && (
              <DetailRow label="Status" value={
                <span style={{
                  color: selectedElement.status === 'running' ? '#10B981' : '#EF4444',
                  fontWeight: 600
                }}>
                  {selectedElement.status}
                </span>
              } />
            )}
            {selectedElement.vmid != null && <DetailRow label="VMID" value={selectedElement.vmid} />}
            {selectedElement.node && <DetailRow label="Host" value={selectedElement.node} />}
            {selectedElement.cpu > 0 && <DetailRow label="CPU" value={`${selectedElement.cpu} cores`} />}
            {selectedElement.mem > 0 && <DetailRow label="Memory" value={`${(selectedElement.mem / 1024 / 1024 / 1024).toFixed(1)} GB`} />}
            {selectedElement.ips && selectedElement.ips.length > 0 && (
              <DetailRow label="IP" value={selectedElement.ips.join(', ')} />
            )}
            {selectedElement.interface && <DetailRow label="Interface" value={selectedElement.interface} />}
            {selectedElement.vlan && <DetailRow label="VLAN" value={selectedElement.vlan} />}
            {selectedElement.zone && <DetailRow label="Zone" value={selectedElement.zone} />}
            {selectedElement.cidr && <DetailRow label="CIDR" value={selectedElement.cidr} />}
            {selectedElement.gateway && <DetailRow label="Gateway" value={selectedElement.gateway} />}
          </div>
        </div>
      )}
    </div>
  );
};

const DetailRow = ({ label, value }) => (
  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
    <span style={{ color: '#6B7280', fontWeight: 500 }}>{label}</span>
    <span style={{ color: '#1F2937' }}>{value}</span>
  </div>
);

const LegendDot = ({ color, label }) => (
  <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
    <span style={{ display: 'inline-block', width: 10, height: 10, borderRadius: '50%', background: color }} />
    {label}
  </span>
);

const LegendRect = ({ color, label }) => (
  <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
    <span style={{ display: 'inline-block', width: 14, height: 10, borderRadius: 3, background: color }} />
    {label}
  </span>
);

export default TopologyView;
