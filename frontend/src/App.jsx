import { useState, useEffect } from 'react'
import './App.css'

const API_BASE = (import.meta.env.VITE_API_URL || 'https://vycka12-binance-data-backend.hf.space') + '/api'; // Build trigger v3 - 2026-03-10

function App() {
  const [symbols, setSymbols] = useState(['BTC/USDT']);
  const [selectedSymbol, setSelectedSymbol] = useState('BTC/USDT');
  const [interval, setInterval] = useState('1m');
  const [dataType, setDataType] = useState('Klines (OHLCV)');

  // Date setup (last 7 days default)
  const defaultEnd = new Date().toISOString().split('T')[0];
  const defaultStart = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
  const [startDate, setStartDate] = useState(defaultStart);
  const [endDate, setEndDate] = useState(defaultEnd);

  // Status and data
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);
  const [previewData, setPreviewData] = useState([]);
  const [csvData, setCsvData] = useState(null);
  const [modalCmd, setModalCmd] = useState(null);
  const [dollarThreshold, setDollarThreshold] = useState(1000000);
  const [aggMode, setAggMode] = useState('Standard (Klines + Liq)');

  // Progress simulation (since real SSE would require more backend work)
  const [progress, setProgress] = useState(0);

  const intervals = ['1s', '1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w', '1mo'];
  const dataTypes = ['Klines (OHLCV)', 'Liquidations', 'AggTrades', 'Dollar Bars (ML Ready)', 'Volume Bars (ML Ready)', 'VPIN (Flow Toxicity)', 'CDF Table (Flow Toxicity)', 'Time-Series Aggregator (Cloud)'];

  useEffect(() => {
    fetch(`${API_BASE}/symbols`)
      .then(res => res.json())
      .then(data => {
        if (data.symbols && data.symbols.length > 0) {
          setSymbols(data.symbols);
          if (data.symbols.includes('BTC/USDT')) {
            setSelectedSymbol('BTC/USDT');
          } else {
            setSelectedSymbol(data.symbols[0]);
          }
        }
      })
      .catch(err => console.error("Error fetching symbols:", err));
  }, []);

  // Simulate progress bar — slower for bigger date ranges
  useEffect(() => {
    let intervalId;
    if (loading && progress < 90) {
      const start = new Date(startDate);
      const end = new Date(endDate);
      const daysDiff = Math.max(1, (end - start) / (1000 * 60 * 60 * 24));
      // Slower increments for bigger date ranges
      const increment = daysDiff > 365 ? 0.5 : daysDiff > 30 ? 2 : 10;

      intervalId = window.setInterval(() => {
        setProgress(p => Math.min(p + Math.random() * increment, 90));
      }, 1000);
    } else if (!loading && progress > 0 && progress < 100) {
      setProgress(100);
      setTimeout(() => setProgress(0), 1000);
    }
    return () => clearInterval(intervalId);
  }, [loading, progress, startDate, endDate]);

  const handleDownload = async () => {
    setLoading(true);
    setError(null);
    setSuccessMsg(null);
    setPreviewData([]);
    setCsvData(null);
    setModalCmd(null);
    setProgress(2);

    try {
      const response = await fetch(`${API_BASE}/download`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol: selectedSymbol,
          interval: interval,
          data_type: dataType,
          start_date: startDate,
          end_date: endDate,
          threshold: dollarThreshold,
          agg_mode: aggMode
        })
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || "Įvyko nežinoma klaida");
      }

      if (result.success) {
        let msg = `✅ Apdorojimas baigtas! Iš viso: ${result.row_count} eilučių.`;
        if (result.hf_url) {
          msg += ` Failas automatiškai įkeltas į Hugging Face!`;
        }
        setSuccessMsg(msg);
        setPreviewData(result.preview);
        setCsvData(result.csv_data);
        if (result.hf_url) {
          // You could also store this URL in state if you want to show a dedicated button
          console.log("HF URL:", result.hf_url);
        }
      } else {
        setError(result.message || "Duomenų nerasta.");
      }

    } catch (err) {
      setError(`❌ Klaida: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const downloadCsvFile = () => {
    if (!csvData) return;
    const blob = new Blob([csvData], { type: 'text/csv;charset=utf-8;' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${selectedSymbol.replace('/', '_')}_${dataType.split(' ')[0]}_${startDate}_${endDate}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  };

  return (
    <div className="app-container">
      {/* Sidebar */}
      <aside className="sidebar glass-panel">
        <h2>⚙️ Konfigūracija</h2>

        <div className="form-group">
          <label>Pasirinkite simbolį</label>
          <select
            className="form-control"
            value={selectedSymbol}
            onChange={e => setSelectedSymbol(e.target.value)}
          >
            {symbols.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>

        <div className="form-group">
          <label>Intervalas (Timeframe)</label>
          <select
            className="form-control"
            value={interval}
            onChange={e => setInterval(e.target.value)}
          >
            {intervals.map(i => <option key={i} value={i}>{i}</option>)}
          </select>
        </div>

        <div className="form-group">
          <label>Duomenų tipas</label>
          <div className="radio-group">
            {dataTypes.map(type => (
              <label key={type} className="radio-label">
                <input
                  type="radio"
                  name="dataType"
                  value={type}
                  checked={dataType === type}
                  onChange={e => setDataType(e.target.value)}
                />
                {type}
              </label>
            ))}
          </div>
        </div>

        {(dataType === 'Dollar Bars (ML Ready)' || dataType === 'Volume Bars (ML Ready)') && (
          <div className="form-group">
            <label>{dataType === 'Dollar Bars (ML Ready)' ? 'Dollar Threshold ($)' : 'Volume Threshold (Quantity)'}</label>
            <input
              type="number"
              className="form-control"
              value={dollarThreshold}
              onChange={e => setDollarThreshold(Number(e.target.value))}
              step={dataType === 'Dollar Bars (ML Ready)' ? "100000" : "100"}
            />
          </div>
        )}

        {(dataType === 'VPIN (Flow Toxicity)' || dataType === 'CDF Table (Flow Toxicity)') && (
          <div className="form-group">
            <label>Buckets Per Day (Resolution)</label>
            <input
              type="number"
              className="form-control"
              value={dollarThreshold} // Reusing threshold state for buckets_per_day
              onChange={e => setDollarThreshold(Number(e.target.value))}
              step="10"
            />
            <small style={{ color: 'var(--text-secondary)', fontSize: '0.75rem' }}>Rekomenduojama: 50-100</small>
          </div>
        )}

        {dataType === 'Time-Series Aggregator (Cloud)' && (
          <div className="form-group">
            <label>Cloud Aggregation Mode</label>
            <div className="radio-group">
              {['Standard (Klines + Liq)', 'Dollar Bars'].map(mode => (
                <label key={mode} className="radio-label">
                  <input
                    type="radio"
                    name="aggMode"
                    value={mode}
                    checked={aggMode === mode}
                    onChange={e => setAggMode(e.target.value)}
                  />
                  {mode}
                </label>
              ))}
            </div>
          </div>
        )}

        <div className="date-row">
          <div className="form-group">
            <label>Pradžia</label>
            <input
              type="date"
              className="form-control"
              value={startDate}
              onChange={e => setStartDate(e.target.value)}
            />
          </div>
          <div className="form-group">
            <label>Pabaiga</label>
            <input
              type="date"
              className="form-control"
              value={endDate}
              onChange={e => setEndDate(e.target.value)}
            />
          </div>
        </div>

        <button
          className="btn-primary"
          onClick={handleDownload}
          disabled={loading}
        >
          {loading ? '⏳ Apdorojama...' : '🚀 Vykdyti'}
        </button>
      </aside>

      {/* Main Content */}
      <main className="main-content">
        <header className="dashboard-header glass-panel">
          <h1>📊 Binance {dataType} Dashboard</h1>
          <div className="status-bar">
            <div className="status-item">Simbolis: <span>{selectedSymbol}</span></div>
            <div className="status-item">Intervalas: <span>{interval}</span></div>
            <div className="status-item">Laikotarpis: <span>{startDate} iki {endDate}</span></div>
          </div>
        </header>

        <section className="results-area glass-panel">
          {loading ? (
            <div className="loader-container">
              <div className="loader-neon"></div>
              <h3 className="gradient-text">Kraunami duomenys...</h3>
              <p className="loader-info">Apdorojama: <b>{dataType}</b></p>
              {(() => {
                const days = Math.max(1, (new Date(endDate) - new Date(startDate)) / (1000 * 60 * 60 * 24));
                if (days > 365) return <span className="loader-timer">⏱️ Didelis laikotarpis ({Math.round(days / 365)} m.) — gali užtrukti 2-5 min.</span>;
                if (days > 30) return <span className="loader-timer">⏱️ ~{Math.round(days / 30)} mėn. duomenų — gali užtrukti ~1-2 min.</span>;
                return null;
              })()}
              <div className="progress-bar-container">
                <div className="progress-bar" style={{ width: `${progress}%` }}></div>
              </div>
            </div>
          ) : (
            <>
              {error && <div className="alert alert-error">{error}</div>}
              {successMsg && <div className="alert alert-success">{successMsg}</div>}

              {modalCmd && (
                <div className="alert alert-info" style={{ flexDirection: 'column' }}>
                  <strong>🌩️ Modal Cloud Data Processing</strong>
                  <span>Ši funkcija skirta didelių duomenų kiekių apjungimui (2+ metai). Vykdykite terminale:</span>
                  <div className="code-block">{modalCmd}</div>
                </div>
              )}

              {!modalCmd && previewData.length > 0 ? (
                <>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <h3 style={{ color: 'var(--text-primary)' }}>Duomenų peržiūra (Paskutinės 100 eilučių)</h3>
                    <button className="btn-primary" onClick={downloadCsvFile} style={{ marginTop: 0, padding: '8px 16px', fontSize: '0.9rem' }}>
                      💾 Atsisiųsti CSV failą
                    </button>
                  </div>
                  <div className="table-container">
                    <table>
                      <thead>
                        <tr>
                          {Object.keys(previewData[0]).map(key => (
                            <th key={key}>{key}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {previewData.map((row, i) => (
                          <tr key={i}>
                            {Object.values(row).map((val, j) => (
                              <td key={j}>{val}</td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </>
              ) : (
                !error && !loading && !modalCmd && (
                  <div className="empty-state">
                    Pasirinkite nustatymus ir spauskite "Vykdyti", kad atsisiųstumėte duomenis.
                  </div>
                )
              )}
            </>
          )}
        </section>
      </main>
    </div>
  )
}

export default App
