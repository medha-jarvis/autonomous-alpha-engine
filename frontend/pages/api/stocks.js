// API: fetch portfolio stock list and status
const TYPESENSE_URL = process.env.TYPESENSE_URL || 'http://localhost:8108';
const TYPESENSE_KEY = process.env.TYPESENSE_API_KEY || 'HermesInvestSearchKey2026';

// Portfolio stocks from config
const PORTFOLIO = [
  'INTERARCH','SAGILITY','KAYNES','REDINGTON','KALYANKJIL','AAVAS','ANGELONE',
  'ASTRAL','BAJAJELEC','BHARATFORG','BLUESTARCO','BSE','CESC','COFORGE','DIXON',
  'DREAMFOLK','GODREJCP','HAL','HCLTECH','HDFCBANK','ICICIBANK','INFY','IRFC',
  'LT','MCDOWELL-N','MOTHERSON','PCBL','RADICO','RELAXO','TATACONSUM','ZOMATO',
];

export default async function handler(req, res) {
  try {
    // Get latest transcript date per ticker
    const stocksWithData = [];
    
    for (const ticker of PORTFOLIO) {
      const params = new URLSearchParams({
        q: '*',
        query_by: 'ticker',
        filter_by: `ticker:=${ticker}`,
        per_page: 1,
        sort_by: 'created_at:desc',
      });

      const url = `${TYPESENSE_URL}/collections/concall_transcripts/documents/search?${params}`;
      const response = await fetch(url, {
        headers: { 'X-TYPESENSE-API-KEY': TYPESENSE_KEY },
      });
      
      if (response.ok) {
        const data = await response.json();
        stocksWithData.push({
          ticker,
          transcript_count: data.found || 0,
          latest: data.hits?.[0]?.document?.quarter 
            ? `${data.hits[0].document.quarter} ${data.hits[0].document.fiscal_year}`
            : null,
        });
      } else {
        stocksWithData.push({ ticker, transcript_count: 0, latest: null });
      }
    }

    res.status(200).json({ stocks: stocksWithData, total: PORTFOLIO.length });
  } catch (error) {
    console.error('Stocks API error:', error);
    res.status(500).json({ error: error.message });
  }
}