"""Thin FastAPI-style proxy server using Python http.server.
Exposes API endpoints that Vercel frontend can call."""
import json, urllib.request, os, http.server

TYPESENSE_URL = "http://localhost:8108"
TYPESENSE_KEY = "HermesInvestSearchKey2026"
API_KEY = os.environ.get("ALPHA_API_KEY", "alpha-secret-key-2026")

class ProxyHandler(http.server.BaseHTTPRequestHandler):
    def _send(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def do_OPTIONS(self):
        self._send({"ok": True})
    
    def do_GET(self):
        # Auth check
        auth = self.headers.get("Authorization", "")
        if auth != f"Bearer {API_KEY}":
            self._send({"error": "unauthorized"}, 401)
            return
        
        path = self.path
        
        # Health
        if path == "/health":
            try:
                req = urllib.request.Request(f"{TYPESENSE_URL}/health")
                req.add_header("X-TYPESENSE-API-KEY", TYPESENSE_KEY)
                resp = urllib.request.urlopen(req, timeout=5)
                self._send(json.loads(resp.read()))
            except Exception as e:
                self._send({"ok": False, "error": str(e)}, 500)
            return
        
        # Search transcripts
        if path.startswith("/api/search"):
            from urllib.parse import urlparse, parse_qs
            params = parse_qs(urlparse(path).query)
            q = params.get("q", [""])[0]
            limit = params.get("limit", ["10"])[0]
            ticker = params.get("ticker", [""])[0]
            
            ts_params = f"q={urllib.request.quote(q or '*')}&query_by=full_text,prepared_remarks,qa_section,ticker&per_page={limit}"
            if ticker:
                ts_params += f"&filter_by=ticker:={ticker}"
            
            url = f"{TYPESENSE_URL}/collections/concall_transcripts/documents/search?{ts_params}"
            req = urllib.request.Request(url)
            req.add_header("X-TYPESENSE-API-KEY", TYPESENSE_KEY)
            try:
                resp = urllib.request.urlopen(req, timeout=10)
                self._send(json.loads(resp.read()))
            except Exception as e:
                self._send({"error": str(e)}, 500)
            return
        
        # Stock evaluations
        if path.startswith("/api/stock/"):
            ticker = path.split("/api/stock/")[1].split("/")[0].upper()
            results = {"ticker": ticker, "transcripts": [], "evaluations": []}
            
            for col in ["concall_transcripts", "evaluations"]:
                params = f"q=*&query_by=ticker&filter_by=ticker:={ticker}&per_page=50&sort_by=created_at:desc"
                url = f"{TYPESENSE_URL}/collections/{col}/documents/search?{params}"
                req = urllib.request.Request(url)
                req.add_header("X-TYPESENSE-API-KEY", TYPESENSE_KEY)
                try:
                    resp = urllib.request.urlopen(req, timeout=10)
                    data = json.loads(resp.read())
                    key = "transcripts" if col == "concall_transcripts" else "evaluations"
                    results[key] = data.get("hits", [])
                except:
                    pass
            
            self._send(results)
            return
        
        # Portfolio stocks list
        if path == "/api/stocks":
            portfolio = ["INTERARCH","SAGILITY","KAYNES","REDINGTON","KALYANKJIL","AAVAS","ANGELONE",
                "ASTRAL","BAJAJELEC","BHARATFORG","BLUESTARCO","BSE","CESC","COFORGE","DIXON",
                "DREAMFOLK","GODREJCP","HAL","HCLTECH","HDFCBANK","ICICIBANK","INFY","IRFC",
                "LT","MCDOWELL-N","MOTHERSON","PCBL","RADICO","RELAXO","TATACONSUM","ZOMATO"]
            
            stocks = []
            for t in portfolio:
                params = f"q=*&query_by=ticker&filter_by=ticker:={t}&per_page=1&sort_by=created_at:desc"
                url = f"{TYPESENSE_URL}/collections/concall_transcripts/documents/search?{params}"
                req = urllib.request.Request(url)
                req.add_header("X-TYPESENSE-API-KEY", TYPESENSE_KEY)
                try:
                    resp = urllib.request.urlopen(req, timeout=5)
                    data = json.loads(resp.read())
                    count = data.get("found", 0)
                    latest = None
                    if data.get("hits"):
                        d = data["hits"][0]["document"]
                        latest = f"{d.get('quarter','?')} {d.get('fiscal_year','?')}"
                    stocks.append({"ticker": t, "transcript_count": count, "latest": latest})
                except:
                    stocks.append({"ticker": t, "transcript_count": 0, "latest": None})
            
            self._send({"stocks": stocks, "total": len(portfolio)})
            return
        
        self._send({"error": "not found"}, 404)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8700))
    server = http.server.HTTPServer(("0.0.0.0", port), ProxyHandler)
    print(f"Alpha Engine API Proxy running on port {port}")
    server.serve_forever()
