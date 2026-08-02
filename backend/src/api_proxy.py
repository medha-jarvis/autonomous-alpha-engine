"""Thin proxy server using Python http.server.
Accepts both Typesense-style (X-TYPESENSE-API-KEY) and Bearer auth.
Proxies search/stocks/evaluations to local Typesense."""

import json, urllib.request, os, http.server, sys
from urllib.parse import urlparse, parse_qs

TYPESENSE_URL = os.environ.get("TYPESENSE_URL", "http://localhost:8108")
TYPESENSE_KEY = os.environ.get("TYPESENSE_API_KEY", "HermesInvestSearchKey2026")
API_KEY = os.environ.get("ALPHA_API_KEY", "alpha-secret-key-2026")

COLLECTIONS = {
    "concall_transcripts": "concall_transcripts",
}

class ProxyHandler(http.server.BaseHTTPRequestHandler):
    def _send(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type, X-TYPESENSE-API-KEY")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _get_ts_key(self):
        """Get Typesense API key from request headers."""
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            key = auth[7:]
            if key == API_KEY:
                return TYPESENSE_KEY
        ts_key = self.headers.get("X-TYPESENSE-API-KEY", "")
        if ts_key:
            return ts_key
        return TYPESENSE_KEY  # default

    def do_OPTIONS(self):
        self._send({"ok": True})

    def _proxy_ts(self, path):
        """Proxy request to Typesense."""
        ts_key = self._get_ts_key()
        query = urlparse(self.path).query
        ts_url = f"{TYPESENSE_URL}{path}"
        if query:
            ts_url += "?" + query
        try:
            req = urllib.request.Request(ts_url)
            req.add_header("X-TYPESENSE-API-KEY", ts_key)
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read())
            self._send(data)
        except urllib.error.HTTPError as e:
            body = e.read().decode() if e.fp else "{}"
            try:
                self._send({"error": json.loads(body)}, e.code)
            except:
                self._send({"error": body}, e.code)
        except Exception as e:
            self._send({"error": str(e)}, 500)

    def do_GET(self):
        path = urlparse(self.path).path

        # Health check
        if path == "/health":
            try:
                req = urllib.request.Request(f"{TYPESENSE_URL}/health")
                req.add_header("X-TYPESENSE-API-KEY", self._get_ts_key())
                resp = urllib.request.urlopen(req, timeout=5)
                self._send(json.loads(resp.read()))
            except Exception as e:
                self._send({"ok": False, "error": str(e)}, 500)
            return

        # /api/stocks - list all portfolio stocks with transcript counts
        if path == "/api/stocks":
            try:
                from collections import Counter
                from config import config
                stocks_list = list(config.portfolio_stocks.keys())
                
                # Use Typesense aggregation to count docs per ticker efficiently
                # Search once with high per_page and facet by ticker
                params = "q=*&query_by=ticker&per_page=250&facet_by=ticker&max_facet_values=100"
                req = urllib.request.Request(
                    f"{TYPESENSE_URL}/collections/concall_transcripts/documents/search?{params}")
                req.add_header("X-TYPESENSE-API-KEY", self._get_ts_key())
                resp = urllib.request.urlopen(req, timeout=10)
                data = json.loads(resp.read())
                
                # Build counts from facets (accurate totals from Typesense)
                counts = {}
                total_found = data.get("found", 0)
                if total_found > 250:
                    # For large collections, count per-ticker using found count
                    # Use facet counts instead
                    for f in data.get("facet_counts", []):
                        for v in f.get("counts", []):
                            counts[v["value"]] = v["count"]
                else:
                    # Small collection: count from hits directly
                    hits = data.get("hits", [])
                    tickers_found = [h.get("document", {}).get("ticker", "") for h in hits]
                    counts = dict(Counter(tickers_found))
                
                stocks = []
                total = 0
                for s in stocks_list:
                    c = counts.get(s, 0)
                    stocks.append({"ticker": s, "transcripts": c})
                    total += c
                
                # Update total if we used facets
                if total_found > 250 and counts:
                    total = total_found
                
                self._send({"stocks": stocks, "total": total})
            except Exception as e:
                self._send({"stocks": [], "error": str(e)})
            return

        # /api/search - search transcripts
        if path == "/api/search":
            params = parse_qs(urlparse(self.path).query)
            q = params.get("q", ["*"])[0]
            limit = params.get("limit", ["10"])[0]
            ticker = params.get("ticker", [""])[0]

            ts_params = f"q={urllib.request.quote(q)}&query_by=full_text,prepared_remarks,qa_section,company_name,ticker&per_page={limit}&sort_by=_text_match:desc"
            if ticker:
                ts_params += f"&filter_by=ticker:={ticker}"

            try:
                req = urllib.request.Request(
                    f"{TYPESENSE_URL}/collections/concall_transcripts/documents/search?{ts_params}")
                req.add_header("X-TYPESENSE-API-KEY", self._get_ts_key())
                resp = urllib.request.urlopen(req, timeout=10)
                data = json.loads(resp.read())
                self._send(data)
            except Exception as e:
                self._send({"error": str(e)}, 500)
            return

        # /api/evaluations - get evaluations
        if path.startswith("/api/evaluations"):
            ticker = parse_qs(urlparse(self.path).query).get("ticker", [""])[0]
            try:
                ts_params = "q=*&query_by=ticker&per_page=20&sort_by=date:desc"
                if ticker:
                    ts_params += f"&filter_by=ticker:={ticker}"
                req = urllib.request.Request(
                    f"{TYPESENSE_URL}/collections/evaluations/documents/search?{ts_params}")
                req.add_header("X-TYPESENSE-API-KEY", self._get_ts_key())
                resp = urllib.request.urlopen(req, timeout=10)
                data = json.loads(resp.read())
                self._send(data)
            except urllib.error.HTTPError:
                # evaluations collection may not exist yet
                self._send({"found": 0, "hits": []})
            except Exception as e:
                self._send({"found": 0, "hits": [], "error": str(e)})
            return

        # Generic proxy: pass any /collections/ path straight to Typesense
        if path.startswith("/collections/"):
            self._proxy_ts(path)
            return

        self._send({"error": "not found"}, 404)

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    print(f"Alpha Engine API Proxy running on port {port}")
    print(f"Typesense URL: {TYPESENSE_URL}")
    server = http.server.HTTPServer(("0.0.0.0", port), ProxyHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down...")
        server.server_close()