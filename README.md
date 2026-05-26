# Qualitative Analysis Toolkit

Hosted web application for **rigorous thematic analysis** following Braun & Clarke's (2006) six-phase framework. Features AI-guided workflow, transcript upload/paste, interactive coding, theme building, and publication-ready PDF/DOCX report generation.

## What it does

- **AI-Guided Analysis**: Fireworks AI walks you through all six phases of thematic analysis
- **Data Input**: Paste text directly or upload transcripts (TXT, DOCX, PDF, CSV, Excel)
- **Structured Workspace**: Phase-specific tools — source management, coding tables, theme builder, report preview
- **Thematic Maps**: Auto-generated visual maps (initial → refined → final)
- **Publication Outputs**: Downloadable PDF reports with embedded maps and visuals, plus DOCX for Word users
- **MAXQDA Compatible**: Still parses `.qdpx` REFI-QDA exports via `analyse.py`

## Architecture

```
React SPA (Vite + Tailwind)  <--->  FastAPI (Python)
  Chat/Workspace UI                  PostgreSQL / SQLite
  Phase-specific panels              Fireworks AI API
  File upload & paste                PDF/DOCX/Map generation
```

## Local Development

### Backend

```bash
pip install -r requirements.txt
uvicorn backend.app.main:app --reload
```

The API runs at `http://localhost:8000`. Set `FIREWORKS_API_KEY` in a `.env` file (see `.env.example`).

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The UI runs at `http://localhost:3000` and proxies API calls to `:8000`.

### Build for production

```bash
cd frontend
npm run build
```

Static files are output to `frontend/dist/` and served by the FastAPI app.

## Railway Deployment

1. **Create a Railway project** and connect your GitHub repo.
2. **Add environment variables** in Railway Dashboard:
    - `FIREWORKS_API_KEY` — required for AI analysis
    - `FIREWORKS_MODEL` — model to use (default: accounts/fireworks/models/qwen3p6-plus)
    - `DATABASE_URL` — Railway Postgres URL (auto-provisioned)
    - `REDIS_URL` — Railway Redis URL (optional, for Celery jobs)
3. **Deploy** — `railway.json` configures the build and start commands.

The app will:
- Build the React frontend
- Start FastAPI on the Railway-assigned `$PORT`
- Serve API at `/api/*` and the SPA at `/`
- Persist uploads and reports to a Railway volume mounted at `/data`

## API Quick Reference

| Endpoint | Method | Description |
|---|---|---|
| `/api/health` | GET | Health check |
| `/api/projects/` | POST | Create project |
| `/api/sources/upload` | POST | Upload transcript file |
| `/api/sources/paste` | POST | Paste transcript text |
| `/api/analysis/chat` | POST | Send phase chat message to AI |
| `/api/analysis/generate-report/{id}` | POST | Generate PDF/DOCX report |

## Legacy: MAXQDA Parser

The original `analyse.py` script is still available for local REFI-QDA parsing:

```bash
python analyse.py --project sample_project.qdpx --output report/
```

## Methods

Supports Braun & Clarke (2006) thematic analysis six-phase framework:
1. Familiarisation with data
2. Generating initial codes
3. Searching for themes
4. Reviewing themes
5. Defining and naming themes
6. Producing the report

## Author

Dr. Sandeep Grover — PhD, 10+ years applied research, 60+ peer-reviewed publications
