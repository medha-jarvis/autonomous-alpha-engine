import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';

const API = process.env.NEXT_PUBLIC_TUNNEL_URL || 'https://known-zones-responsibility-even.trycloudflare.com';

export default function StockDetail() {
  const router = useRouter();
  const { ticker } = router.query;
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!ticker) return;
    const params = new URLSearchParams({ ticker });
    fetch(`${API}/api/evaluations?${params}`)
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, [ticker]);

  if (loading) return <div style={styles.container}><p>Loading...</p></div>;
  if (!data) return <div style={styles.container}><p>No data for {ticker}</p></div>;

  // Group evaluations by transcript
  const evalByTranscript = {};
  (data.evaluations || []).forEach(e => {
    const tid = e.document.transcript_id;
    if (!evalByTranscript[tid]) evalByTranscript[tid] = [];
    evalByTranscript[tid].push(e.document);
  });

  return (
    <div style={styles.container}>
      <a href="/" style={styles.backLink}>← Dashboard</a>
      <h1 style={{ fontSize: 28, fontWeight: 700 }}>{ticker?.toUpperCase()}</h1>
      <p style={{ color: '#666' }}>
        {data.total_transcripts} transcript(s) · {data.total_evals} evaluation(s)
      </p>

      {/* Transcripts */}
      <h2 style={styles.sectionTitle}>Transcripts</h2>
      {(data.transcripts || []).map(tx => (
        <div key={tx.document.news_id} style={styles.card}>
          <div style={{ fontWeight: 600 }}>
            {tx.document.quarter} {tx.document.fiscal_year}
            <span style={{ marginLeft: 8, fontSize: 13, color: '#666', fontWeight: 400 }}>
              {new Date(tx.document.created_at * 1000).toLocaleDateString()}
            </span>
          </div>
          <div style={{ fontSize: 13, color: '#475569', marginTop: 4 }}>
            {tx.document.subcategory}
          </div>
          {tx.document.pdf_url_r2 && (
            <a href={tx.document.pdf_url_r2} target="_blank" rel="noopener" style={styles.link}>
              📄 View PDF
            </a>
          )}
        </div>
      ))}

      {/* Evaluations grouped by transcript */}
      {Object.entries(evalByTranscript).length > 0 && (
        <>
          <h2 style={styles.sectionTitle}>AI Evaluations</h2>
          {Object.entries(evalByTranscript).map(([txId, evals]) => (
            <div key={txId} style={{ marginBottom: 20 }}>
              <h3 style={{ fontSize: 15, color: '#64748b', marginBottom: 8 }}>Transcript: {txId.slice(0, 12)}...</h3>
              {evals.map(e => (
                <div key={`${e.uc_number}-${e.transcript_id}`} style={{
                  ...styles.card, borderLeft: `4px solid ${e.alert_triggered ? '#ef4444' : '#22c55e'}`,
                }}>
                  <div style={{ fontWeight: 600, fontSize: 14 }}>
                    UC-{String(e.uc_number).padStart(2, '0')}: {e.uc_name}
                    {e.alert_triggered && <span style={{ marginLeft: 8, color: '#ef4444' }}>🚨</span>}
                  </div>
                  <div style={{ fontSize: 13, color: '#475569', marginTop: 4, whiteSpace: 'pre-wrap' }}>
                    {formatEvalResult(e.result_json)}
                  </div>
                </div>
              ))}
            </div>
          ))}
        </>
      )}

      {data.evaluations?.length === 0 && data.transcripts?.length === 0 && (
        <div style={{ padding: 40, textAlign: 'center', color: '#94a3b8' }}>
          ⏳ No data yet. The pipeline will process this stock on the next poll cycle.
        </div>
      )}
    </div>
  );
}

function formatEvalResult(jsonStr) {
  try {
    const obj = JSON.parse(jsonStr);
    return Object.entries(obj)
      .filter(([_, v]) => v !== null && v !== '' && !(Array.isArray(v) && v.length === 0))
      .map(([k, v]) => {
        const val = Array.isArray(v) ? v.join(', ') : String(v);
        return `${k}: ${val}`;
      })
      .join('\n');
  } catch {
    return jsonStr?.substring(0, 500) || '';
  }
}

const styles = {
  container: { maxWidth: 1000, margin: '0 auto', padding: 20, fontFamily: 'system-ui, sans-serif' },
  backLink: { display: 'inline-block', marginBottom: 16, color: '#2563eb', textDecoration: 'none', fontSize: 14 },
  sectionTitle: { fontSize: 20, fontWeight: 600, marginTop: 32, marginBottom: 12 },
  card: {
    padding: 16, marginBottom: 8, background: '#fff', borderRadius: 8,
    border: '1px solid #e2e8f0',
  },
  link: { fontSize: 13, color: '#2563eb', marginTop: 4, display: 'inline-block' },
};