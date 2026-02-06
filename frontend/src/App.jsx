import React, { useState, useEffect } from 'react';
import axios from 'axios';
import TopologyView from './components/TopologyView';
import './App.css';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

function App() {
  const [topologyData, setTopologyData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [summary, setSummary] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [refreshInterval, setRefreshInterval] = useState(30);

  const fetchTopology = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // API_BASE_URLが/apiで終わっているので、/topologyのみ追加
      const response = await axios.get(`${API_BASE_URL}/topology`);
      setTopologyData(response.data);
      setSummary(response.data.summary);
      
    } catch (err) {
      console.error('Failed to fetch topology:', err);
      setError(err.response?.data?.error || err.message || 'Failed to fetch topology data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTopology();
  }, []);

  useEffect(() => {
    let intervalId;
    
    if (autoRefresh) {
      intervalId = setInterval(() => {
        fetchTopology();
      }, refreshInterval * 1000);
    }
    
    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [autoRefresh, refreshInterval]);

  return (
    <div className="App">
      <header className="App-header">
        <div className="header-content">
          <h1>Proxmox Network Topology Visualizer</h1>
          
          {summary && (
            <div className="summary">
              <span className="summary-item">
                <strong>Nodes:</strong> {summary.total_nodes}
              </span>
              <span className="summary-item">
                <strong>VMs:</strong> {summary.total_vms}
              </span>
              <span className="summary-item">
                <strong>Networks:</strong> {summary.total_networks}
              </span>
              {summary.total_sdn > 0 && (
                <span className="summary-item">
                  <strong>SDN:</strong> {summary.total_sdn}
                </span>
              )}
            </div>
          )}
        </div>
        
        <div className="controls">
          <button onClick={fetchTopology} disabled={loading}>
            {loading ? 'Loading...' : 'Refresh'}
          </button>
          
          <label className="auto-refresh-control">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
            Auto-refresh
          </label>
          
          {autoRefresh && (
            <select
              value={refreshInterval}
              onChange={(e) => setRefreshInterval(Number(e.target.value))}
              className="refresh-interval"
            >
              <option value={10}>10s</option>
              <option value={30}>30s</option>
              <option value={60}>1m</option>
              <option value={300}>5m</option>
            </select>
          )}
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
      
      <footer className="App-footer">
        <div className="legend">
          <h4>Legend</h4>
          <div className="legend-items">
            <div className="legend-item">
              <span className="legend-color" style={{ backgroundColor: '#4A90E2' }}></span>
              Physical Node
            </div>
            <div className="legend-item">
              <span className="legend-color" style={{ backgroundColor: '#7ED321' }}></span>
              VM
            </div>
            <div className="legend-item">
              <span className="legend-color" style={{ backgroundColor: '#F5A623' }}></span>
              Container
            </div>
            <div className="legend-item">
              <span className="legend-color" style={{ backgroundColor: '#BD10E0' }}></span>
              Bridge
            </div>
            <div className="legend-item">
              <span className="legend-color" style={{ backgroundColor: '#50E3C2' }}></span>
              VLAN
            </div>
            <div className="legend-item">
              <span className="legend-color" style={{ backgroundColor: '#FF6B6B' }}></span>
              SDN VNET
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
