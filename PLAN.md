# Autonomous Alpha Engine — Build Plan

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                     VPS (KVM2, 4-8GB RAM)           │
│                                                     │
│  ┌──────────┐    ┌──────────────┐   ┌───────────┐  │
│  │ BSE      │───▶│ PDF          │──▶│ Typesense  │  │
│  │ Poller   │    │ Processor    │   │ (:8108)   │  │
│  │ (15min)  │    │ (PyMuPDF)    │   │ (RAM: 300M)│  │
│  └────┬─────┘    └──┬───────────┘   └───────────┘  │
│       │             │                               │
│       │             ▼                               │
│       │    ┌──────────────────┐                     │
│       │    │ Cloudflare R2     │  ┌──────────────┐  │
│       └───▶│ (PDF Storage)    │  │ 20 Evaluation │  │
│            │ concall-alpha-    │  │ Pipelines     │  │
│            │ engine bucket     │  │ (Async LLM)   │  │
│            └──────────────────┘  └──────┬─────────┘  │
│                                         │            │
│                                         ▼            │
│                                  ┌──────────────┐   │
│                                  │ Telegram      │   │
│                                  │ Alert Engine  │   │
│                                  └──────────────┘   │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
               ┌──────────────┐
               │ Vercel       │
               │ (Next.js)    │
               │ - Dashboard  │
               │ - Search     │
               │ - Stock Mgmt │
               └──────────────┘
```

## File Tree

```
alpha-engine/
├── backend/
│   ├── src/
│   │   ├── __init__.py
│   │   ├── config.py              # All env vars, constants
│   │   ├── bse_client.py          # BSE API wrapper (bse library)
│   │   ├── poller.py              # Cron entrypoint: check for new filings
│   │   ├── pdf_processor.py       # Download PDF, extract text, chunk
│   │   ├── r2_storage.py          # Cloudflare R2 upload/download
│   │   ├── typesense_client.py    # Typesense index/search helpers
│   │   ├── prompts.py             # All 20 evaluation prompts
│   │   ├── evaluator.py           # Async LLM runner (aiohttp)
│   │   ├── alerter.py             # Telegram alert dispatcher
│   │   └── orchestrator.py        # Main: poll → process → index → eval → alert
│   ├── requirements.txt
│   └── scripts/
│       ├── backfill.py            # Initial backfill for portfolio stocks
│       └── install-typesense.sh   # Typesense download + setup
├── frontend/
│   ├── pages/
│   │   ├── index.js               # Dashboard
│   │   ├── search.js              # Full-text search
│   │   ├── stocks/
│   │   │   └── [ticker].js        # Stock detail + evaluations
│   │   └── api/
│   │       ├── search.js          # Typesense search proxy
│   │       ├── stocks.js          # CRUD for tracked stocks
│   │       └── evaluations.js     # Eval results for a stock
│   ├── package.json
│   ├── vercel.json
│   └── next.config.js
├── .env.example
└── PLAN.md
```

## Build Phases

### Phase 0: Infrastructure
- Download + run Typesense server
- Create R2 bucket (`concall-alpha-engine`)
- Verify all env vars accessible

### Phase 1: Backend Pipeline
- **bse_client.py** — wraps `bse` library, gets announcements filtered by subcategory "Earnings Call Transcript", "Analyst / Investor Meet"  
- **poller.py** — cron script: fetch latest announcements for tracked stocks, check against processed set (SQLite dedup), trigger pipeline  
- **pdf_processor.py** — download PDF from `https://www.bseindia.com/xml-data/corpfiling/AttachLive/{uuid}.pdf`, extract text with PyMuPDF, split into Prepared Remarks / Q&A, upload original to R2  
- **typesense_client.py** — manage collections (`concall_transcripts`, `evaluations`), index/query documents  
- **orchestrator.py** — coordinates the full flow

### Phase 2: 20 Evaluation Pipelines
- **prompts.py** — all 20 UC prompt templates with `{current_text}`, `{q_minus_1_json}`, `{qa_text}` etc. interpolation  
- **evaluator.py** — async runner using `aiohttp`, calls OpenRouter with `response_format={"type":"json_object"}`, assembles context (fetches previous quarter data from Typesense), stores results back to Typesense  
- **alerter.py** — checks eval results against thresholds per UC, formats Telegram messages, sends via bot

### Phase 3: Frontend (Vercel)
- Next.js app with 3 main pages
- Serverless API routes proxy to Typesense on VPS (via HTTP)
- Real-time search across all transcripts

### Phase 4: Deployment
- Hermes cron job at 15min interval
- Initial backfill: process latest 8 quarters for all 31 portfolio stocks
- Vercel deploy with env vars

## Blockers Requiring User Input

1. **R2 full credentials** — the PRD had `7c5f7...903a2797527f2ec` (key appears redacted). Need the complete `R2_SECRET_ACCESS_KEY` and `R2_TOKEN_VALUE`.
2. **Portfolio stock list** — I have your 31 stocks from memory. Confirm if this is the list to track, or provide an updated one.
3. **Typesense server** — I'll download and set it up on the VPS. Confirm you want it on port 8108 (default).

## Confirmed Working

- ✅ BSE API (via Python `bse` library, returns announcements with subcategory matching)
- ✅ PDF download from BSE CDN
- ✅ PyMuPDF for text extraction
- ✅ OpenRouter key in env
- ✅ Telegram bot + chat ID in env
- ✅ Typesense API key known
- ✅ 5GB free RAM → typesense will use ~300MB for index
- ✅ 16GB free disk → plenty for code + temp PDFs

Ready to proceed once you confirm the three items above.