// API: fetch evaluations for a stock ticker
const TYPESENSE_URL = process.env.TYPESENSE_URL || 'http://localhost:8108';
const TYPESENSE_KEY = process.env.TYPESENSE_API_KEY || 'HermesInvestSearchKey2026';

export default async function handler(req, res) {
  const { ticker } = req.query;
  
  if (!ticker) {
    return res.status(400).json({ error: 'ticker required' });
  }

  try {
    // Fetch evaluations
    const params = new URLSearchParams({
      q: '*',
      query_by: 'ticker',
      filter_by: `ticker:=${ticker.toUpperCase()}`,
      per_page: 100,
      sort_by: 'created_at:desc',
    });

    const url = `${TYPESENSE_URL}/collections/evaluations/documents/search?${params}`;
    const response = await fetch(url, {
      headers: { 'X-TYPESENSE-API-KEY': TYPESENSE_KEY },
    });

    if (!response.ok) throw new Error(`Typesense error: ${response.status}`);
    const data = await response.json();

    // Fetch transcripts
    const txParams = new URLSearchParams({
      q: '*',
      query_by: 'ticker',
      filter_by: `ticker:=${ticker.toUpperCase()}`,
      per_page: 20,
      sort_by: 'created_at:desc',
    });

    const txUrl = `${TYPESENSE_URL}/collections/concall_transcripts/documents/search?${txParams}`;
    const txResponse = await fetch(txUrl, {
      headers: { 'X-TYPESENSE-API-KEY': TYPESENSE_KEY },
    });
    const txData = txResponse.ok ? await txResponse.json() : { hits: [] };

    res.status(200).json({
      evaluations: data.hits || [],
      transcripts: txData.hits || [],
      total_evals: data.found || 0,
      total_transcripts: txData.found || 0,
    });
  } catch (error) {
    console.error('Stock API error:', error);
    res.status(500).json({ error: error.message });
  }
}