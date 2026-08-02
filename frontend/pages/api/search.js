// API proxy for Typesense search
const TYPESENSE_URL = process.env.TYPESENSE_URL || 'http://localhost:8108';
const TYPESENSE_KEY = process.env.TYPESENSE_API_KEY || 'HermesInvestSearchKey2026';

export default async function handler(req, res) {
  const { q, collection = 'concall_transcripts', limit = 10, filter_by } = req.query;
  
  if (!q && !filter_by) {
    return res.status(400).json({ error: 'Query (q) or filter_by required' });
  }

  try {
    const params = new URLSearchParams({
      q: q || '*',
      query_by: 'full_text,prepared_remarks,qa_section,company_name,ticker',
      per_page: limit,
      sort_by: '_text_match:desc',
    });
    
    if (filter_by) params.set('filter_by', filter_by);

    const url = `${TYPESENSE_URL}/collections/${collection}/documents/search?${params}`;
    const response = await fetch(url, {
      headers: { 'X-TYPESENSE-API-KEY': TYPESENSE_KEY },
    });

    if (!response.ok) {
      throw new Error(`Typesense error: ${response.status}`);
    }

    const data = await response.json();
    res.status(200).json(data);
  } catch (error) {
    console.error('Search API error:', error);
    res.status(500).json({ error: error.message });
  }
}