# DevMind AI Pro — 3D LLM Development Workspace

A professional dark-glass 3D LLM developer dashboard with 12 responsive pages, animated 3D hero/background, chat UI, agent workspace, coding workspace, RAG, prompt lab, model playground, memory, billing, settings and admin.

## Run
```powershell
cd frontend
npm install
npm run dev
```
Open http://localhost:5173

Optional backend:
```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

The frontend works in demo mode without a backend. API integration points are clearly isolated in `src/api.js`.
