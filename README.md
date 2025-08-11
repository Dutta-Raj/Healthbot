# Hugging Face Space — Flask -> Gradio wrapper

This repository runs a simple Gradio-based UI that:
- Displays `templates/index.html` (if present).
- Shows messages stored in a database (Postgres on cloud via DATABASE_URL, or SQLite locally).
- Lets you add messages.

## Deploy on Hugging Face Spaces

1. Create a new Space: https://huggingface.co/spaces
2. Choose a name and set SDK to **Gradio** (Python).
3. Push this repository files to the Space (via the web UI or `git`).
4. If you want to use a Postgres DB, create the external DB (Railway, Supabase, Neon, etc.) and copy the connection string.

### Set secret (DATABASE_URL)
- In your Space → Settings → Secrets, add:
  - Key: `DATABASE_URL`
  - Value: `postgresql://username:password@host:port/databasename`

The app will automatically use Postgres when `DATABASE_URL` is present, otherwise it uses `local.db` (SQLite).

## Local testing
1. Create virtual env and install:
