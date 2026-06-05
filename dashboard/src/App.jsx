import { useState, useEffect } from 'react'
import './App.css'

function App() {
  const [status, setStatus] = useState(false)
  const [stats, setStats] = useState({ 
    total_profit_usdt: 0, 
    trades_executed: 0, 
    ping_ms: 0, 
    active_pairs: 0,
    start_time: null
  })
  const [trades, setTrades] = useState([])
  const [uptime, setUptime] = useState("00:00:00")
  
  const [config, setConfig] = useState({
    api_key: '',
    secret_key: '',
    starting_amount: 100,
    min_profit_threshold: 1.005
  })

  const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

  const fetchState = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/status`)
      const data = await res.json()
      setStatus(data.is_running)
      setStats(data.stats)
      setConfig(data.config)
    } catch (e) {
      console.error("Backend not reachable")
    }
  }

  const fetchTrades = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/trades`)
      const data = await res.json()
      setTrades(data.trades)
    } catch (e) {}
  }

  useEffect(() => {
    fetchState()
    fetchTrades()
    const interval = setInterval(() => {
      fetchState()
      fetchTrades()
    }, 2000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (!status || !stats.start_time) {
      setUptime("00:00:00")
      return
    }
    const interval = setInterval(() => {
      const diff = Math.floor(Date.now() / 1000 - stats.start_time)
      const h = Math.floor(diff / 3600).toString().padStart(2, '0')
      const m = Math.floor((diff % 3600) / 60).toString().padStart(2, '0')
      const s = (diff % 60).toString().padStart(2, '0')
      setUptime(`${h}:${m}:${s}`)
    }, 1000)
    return () => clearInterval(interval)
  }, [status, stats.start_time])

  const handleConfigUpdate = async (e) => {
    e.preventDefault()
    try {
      // We only update the trading parameters, the backend preserves the API keys
      await fetch(`${API_BASE}/api/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          api_key: '************', // Sent as masked to tell backend to preserve existing
          secret_key: '****************',
          starting_amount: config.starting_amount,
          min_profit_threshold: config.min_profit_threshold
        })
      })
    } catch (e) {
      console.error("Error saving config")
    }
  }

  const toggleBot = async () => {
    const endpoint = status ? '/api/stop' : '/api/start'
    try {
      const res = await fetch(`${API_BASE}${endpoint}`, { method: 'POST' })
      const data = await res.json()
      if (data.status === 'success') {
        setStatus(!status)
      } else {
        alert(data.message)
      }
    } catch (e) {
      console.error("Error toggling bot")
    }
  }

  return (
    <div className="app-wrapper">
      <div className="bg-glow orb-1"></div>
      <div className="bg-glow orb-2"></div>
      
      <div className="container">
        
        <header className="header">
          <div className="brand">
            <div className="logo-icon"></div>
            <h1>Quantum Arbitrage</h1>
          </div>
          <div className="header-actions">
            <div className={`status-badge ${status ? 'active' : 'idle'}`}>
              <span className="dot"></span>
              {status ? 'Scanning Engine Active' : 'Engine Standby'}
            </div>
            <button 
              className={`toggle-btn ${status ? 'btn-stop' : 'btn-start'}`}
              onClick={toggleBot}
            >
              {status ? 'Stop Engine' : 'Start Engine'}
            </button>
          </div>
        </header>

        <div className="grid-layout">
          
          <div className="left-column">
            
            <div className="card metrics-card">
              <div className="metric-header">
                <h3>Total Profit Generated</h3>
              </div>
              <div className="profit-display">
                <span className="currency">$</span>
                <span className="amount">{stats.total_profit_usdt.toFixed(2)}</span>
              </div>
              
              <div className="sub-metrics">
                <div className="sub-metric">
                  <span className="label">Cycles</span>
                  <span className="value">{stats.trades_executed}</span>
                </div>
                <div className="sub-metric">
                  <span className="label">Uptime</span>
                  <span className="value">{uptime}</span>
                </div>
                <div className="sub-metric">
                  <span className="label">Ping</span>
                  <span className="value">{stats.ping_ms}ms</span>
                </div>
                <div className="sub-metric">
                  <span className="label">Pairs</span>
                  <span className="value">{stats.active_pairs}</span>
                </div>
              </div>
            </div>

            <div className="card config-card">
              <h3>System Configuration</h3>
              <p className="card-subtitle">Connect to Binance Testnet</p>
              
              <form onSubmit={handleConfigUpdate}>
                <div className="form-row">
                  <div className="form-group">
                    <label>Trade Size (USDT)</label>
                    <input 
                      type="number" 
                      value={config.starting_amount} 
                      onChange={e => setConfig({...config, starting_amount: parseFloat(e.target.value)})} 
                    />
                  </div>
                  <div className="form-group">
                    <label>Min Profit Multiplier</label>
                    <input 
                      type="number" 
                      step="0.001"
                      value={config.min_profit_threshold} 
                      onChange={e => setConfig({...config, min_profit_threshold: parseFloat(e.target.value)})} 
                    />
                  </div>
                </div>
                
                <button type="submit" className="save-btn">Update Configuration</button>
              </form>
            </div>
            
          </div>

          <div className="right-column">
            <div className="card table-card">
              <div className="card-header">
                <h3>Execution Ledger</h3>
                {status && <div className="scanning-indicator">Scanning live orderbooks...</div>}
              </div>
              
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>Time</th>
                      <th>Arbitrage Path</th>
                      <th>Yield</th>
                      <th>Profit (USDT)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trades.length === 0 ? (
                      <tr><td colSpan="4" className="empty-state">No execution data available</td></tr>
                    ) : (
                      trades.map((t, i) => (
                        <tr key={i}>
                          <td className="time-col">{new Date(t.timestamp * 1000).toLocaleTimeString()}</td>
                          <td className="path-col">
                            <div className="path-pill">{t.path}</div>
                          </td>
                          <td className="yield-col">+{t.profit_percentage.toFixed(3)}%</td>
                          <td className="profit-col">+${t.profit_usdt.toFixed(2)}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  )
}

export default App
