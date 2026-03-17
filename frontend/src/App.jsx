import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import TopologyView from './components/TopologyView';
import './App.css';

const API_BASE_URL = '';

function App() {
  const [topologyData, setTopologyData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [summary, setSummary] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [refreshInterval, setRefreshInterval] = useState(30);

  // Filters
  const [hideStoppedVMs, setHideStoppedVMs] = useState(true);
  const [hideHostsEdges, setHideHostsEdges] = useState(true);
  const [hidePhysicalNode, setHidePhysicalNode] = useState(true);

  const fetchTopology = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const params = new URLSearchParams({
        hide_stopped: hideStoppedVMs.toString(),
        hide_hosts_edges: hideHostsEdges.toString(),
        hide_physical_node: hidePhysicalNode.toString()
      });

      const response = await axios.get(`${API_BASE_URL}/api/topology?${params}`);
      setTopologyData(response.data);
      setSummary(response.data.summary);
    } catch (err) {
      console.error('Failed to fetch topology:', err);
      setError(err.response?.data?.error || err.message || 'Failed to fetch topology data');
    } finally {
      setLoading(false);
    }
  }, [hideStoppedVMs, hideHostsEdges, hidePhysicalNode]);

  // Refetch on filter change
  useEffect(() => { fetchTopology(); }, [fetchTopology]);

  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh) return;
    const id = setInterval(fetchTopology, refreshInterval * 1000);
    return () => clearInterval(id);
  }, [autoRefresh, refreshInterval, fetchTopology]);

  return (
    <div className="App">
      <header className="App-header">
        <div className="header-top">
          <h1>Proxmox Topology</h1>
          {summary && (
            <div className="summary-badges">
              <span className="badge badge-running">{summary.running_vms} running</span>
              <span className="badge badge-stopped">{summary.stopped_vms} stopped</span>
              <span className="badge badge-network">{summary.total_networks + summary.total_sdn} networks</span>
            </div>
          )}
        </div>

        <div className="header-controls">
          <div className="filter-group">
            <label className="toggle-control">
              <input type="checkbox" checked={hideStoppedVMs}
                onChange={(e) => setHideStoppedVMs(e.target.checked)} />
              <span>Hide stopped</span>
            </label>
            <label className="toggle-control">
              <input type="checkbox" checked={hideHostsEdges}
                onChange={(e) => setHideHostsEdges(e.target.checked)} />
              <span>Hide host edges</span>
            </label>
            <label className="toggle-control">
              <input type="checkbox" checked={hidePhysicalNode}
                onChange={(e) => setHidePhysicalNode(e.target.checked)} />
              <span>Hide physical node</span>
            </label>
          </div>

          <div className="action-group">
            <button onClick={fetchTopology} disabled={loading} className="btn-refresh">
              {loading ? 'Loading...' : 'Refresh'}
            </button>
            <label className="toggle-control">
              <input type="checkbox" checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)} />
              <span>Auto</span>
            </label>
            {autoRefresh && (
              <select value={refreshInterval}
                onChange={(e) => setRefreshInterval(Number(e.target.value))}
                className="refresh-interval">
                <option value={10}>10s</option>
                <option value={30}>30s</option>
                <option value={60}>1m</option>
                <option value={300}>5m</option>
              </select>
            )}
          </div>
        </div>
      </header>

      <main className="App-main">
        {loading && !topologyData && (
          <div className="loading-container">
            <div className="spinner"></div>
            <p>Loading topology data...</p>
          </div>
        )}

        {error && (
          <div className="error-container">
            <h2>Error</h2>
            <p>{error}</p>
            <button onClick={fetchTopology}>Retry</button>
          </div>
        )}

        {!loading && !error && topologyData && (
          <TopologyView topologyData={topologyData} />
        )}
      </main>
    </div>
  );
}

export default App;
