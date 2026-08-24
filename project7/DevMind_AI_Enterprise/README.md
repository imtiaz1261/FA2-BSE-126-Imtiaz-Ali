# DevMind AI Enterprise — Updated & Fixed

This is the corrected Enterprise build based on the project source used in the conversation.

## Frontend
```powershell
cd frontend
npm install
npm run dev
```
Open http://localhost:5173

## Backend
Open a second PowerShell:
```powershell
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Swagger: http://127.0.0.1:8000/docs

## Fixed
- `ScanEye` import error
- React `useEffect` Promise bug in Memory
- Sidebar reorganized into CORE / BUILD / KNOWLEDGE / EVALUATE / WORKSPACE / ACCOUNT / ADMIN
- FastAPI `current_user` is now a proper `Depends(current_user)` dependency
- Backend includes the API endpoints used by the UI
- CORS configured for Vite
- JWT dependency included (`PyJWT`)
- RAG upload/search, memory, chat, agent, vision and admin endpoints included

## Notes
The API runs in demo mode without an LLM key. Add a real provider integration and production database before deployment.
