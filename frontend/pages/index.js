import { useState, useEffect } from 'react';

export default function Dashboard() {
  const [stocks, setStocks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState(null);

  useEffect(() => {
    fetch('/api/stocks')
      .then(r => r.json())
      .then(d => { setStocks(d.stocks || []); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    const res = await fetch(`/api/search?q=${encodeURIComponent(searchQuery)}&limit=10`);
    const data = await res.json();
    setSearchResults(data);
  };

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: 20, fontFamily: 'system-ui, sans-serif' }}>
      <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 8 }}>🤖 Autonomous Alpha Engine</h1>
      <p style={{ color: '#666', marginBottom: 24 }}>
        Concall transcript intelligence pipeline — {stocks.length} stocks tracked
      </p>

      {/* Search */}
      <form onSubmit={handleSearch} style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', gap: 8 }}>
          <input
            type="text"
            placeholder='Search transcripts... e.g. "margin guidance", "order inflow", "capex plans"'
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            style={{
              flex: 1, padding: '12px 16px', borderRadius: 8, border: '1px solid #ddd',
              fontSize: 16,
            }}
          />
          <button type="submit" style={{
            padding: '12px 24px', borderRadius: 8, border: 'none', background: '#2563eb',
            color: '#fff', fontSize: 16, cursor: 'pointer', fontWeight: 600,
          }}>
            Search
          </button>
        </div>
      </form>

      {/* Search Results */}
      {searchResults && (
        <div style={{ marginBottom: 32, background: '#f8fafc', borderRadius: 12, padding: 20 }}>
          <h2 style={{ fontSize: 18, marginBottom: 12 }}>
            Search: "{searchQuery}" — {searchResults.found || 0} results
          </h2>
          {(searchResults.hits || []).slice(0, 10).map(hit => (
            <div key={hit.document.id || hit.document.news_id} style={{
              padding: '12px 16px', marginBottom: 8, background: '#fff',
              borderRadius: 8, border: '1px solid #e2e8f0',
            }}>
              <div style={{ fontWeight: 600 }}>
                {hit.document.company_name} ({hit.document.ticker})
                <span style={{ color: '#666', fontWeight: 400, marginLeft: 8 }}>
                  {hit.document.quarter} {hit.document.fiscal_year}
                </span>
              </div>
              <div style={{ color: '#475569', fontSize: 14, marginTop: 4 }}>
                {(hit.document.full_text || '').substring(0, 300)}...
              </div>
              {hit.document.pdf_url_r2 && (
                <a href={hit.document.pdf_url_r2} target="_blank" rel="noopener"
                   style={{ fontSize: 13, color: '#2563eb', marginTop: 4, display: 'inline-block' }}>
                  📄 View Full Transcript
                </a>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Portfolio Table */}
      <h2 style={{ fontSize: 20, marginBottom: 12 }}>Portfolio Stocks</h2>
      {loading ? (
        <p>Loading portfolio...</p>
      ) : (
        <div style={{
          display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
          gap: 12,
        }}>
          {stocks.map(s => (
            <a key={s.ticker} href={`/stocks/${s.ticker}`}
               style={{
                 padding: 16, background: '#fff', borderRadius: 10,
                 border: '1px solid #e2e8f0', textDecoration: 'none', color: 'inherit',
                 transition: 'box-shadow 0.15s',
               }}
               onMouseOver={e => e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.1)'}
               onMouseOut={e => e.currentTarget.style.boxShadow = 'none'}
            >
              <div style={{ fontWeight: 700, fontSize: 16 }}>{s.ticker}</div>
              <div style={{ fontSize: 13, color: '#666', marginTop: 4 }}>
                {s.transcript_count > 0
                  ? `📄 ${s.transcript_count} transcript(s) · Latest: ${s.latest || 'N/A'}`
                  : '⏳ No transcripts indexed yet'}
              </div>
            </a>
          ))}
        </div>
      )}

      <footer style={{ marginTop: 48, padding: '20px 0', borderTop: '1px solid #e2e8f0', fontSize: 13, color: '#94a3b8' }}>
        Autonomous Alpha Engine — BSE/NSE concall intelligence pipeline
      </footer>
    </div>
  );
}