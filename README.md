# AI Teleprompter

## Run (two terminals)
```bash
uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
npm --prefix frontend run dev
```

Open <http://127.0.0.1:5173>.