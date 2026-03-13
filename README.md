# MetaB2B Audience Match + AI Ad Builder

This project provides a web interface and API for:

1. Uploading email lists.
2. Matching them into Meta Custom Audiences (Facebook/Instagram).
3. Generating ad creative with an AI prompt.
4. Connecting a user's Meta credentials so campaigns can be run from a single workflow.

## Features

- **Credential onboarding UI** for Meta and AI providers.
- **CSV/TXT email upload parser** with validation.
- **Meta Custom Audience integration** with SHA-256 hashed emails.
- **AI ad generation endpoint** (OpenAI-compatible API).
- **Simple campaign handoff payload** for ad account + page/IG context.

## Project Structure

- `app/main.py` — FastAPI backend with Meta + AI endpoints.
- `static/index.html` — Front-end interface.
- `static/app.js` — UI logic and API calls.
- `.env.example` — Required environment variables.

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open: `http://localhost:8000`

### If you only want to see the interface quickly

If dependencies are not installed yet, you can still preview the UI:

```bash
python -m http.server 8000
```

Then open: `http://localhost:8000/static/index.html`

> Note: this static preview mode will not run API endpoints. Use `uvicorn` for full Meta/AI integration.

## Environment Variables

See `.env.example`.

At a minimum, set:

- `META_GRAPH_VERSION`
- `OPENAI_BASE_URL`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`

## Notes on Meta Integration

For production use, you must:

- Use a Meta App with Marketing API permissions.
- Complete business verification and app review as required by Meta.
- Use system users / long-lived tokens where appropriate.
- Add robust secrets management (Vault/SSM/etc.) instead of plain env files.

## Security

- Emails are hashed before sending to Meta for audience updates.
- This demo keeps credentials in-memory per request and does not persist secrets.
- Add authentication + role-based access before multi-tenant deployment.
