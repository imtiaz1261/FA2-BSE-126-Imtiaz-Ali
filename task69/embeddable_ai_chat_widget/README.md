# Multi-Tenant Embeddable AI Chat Widget
Python 3.11 + FastAPI + Web Component/Shadow DOM + optional Groq.

## Run
py -3.11 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python server.py

Open http://localhost:3000 for the demo and http://localhost:3000/admin for the admin panel.

Embed:
<script src="https://YOUR-DOMAIN/widget.js" data-bot-id="tenant-a"></script>

Demo tenants: tenant-a and tenant-b.
The widget is isolated with Shadow DOM, responsive, has a floating bubble, animation,
tenant branding, custom instructions, and chat history. The admin panel edits both
demo tenants and generates the embed code.

Without GROQ_API_KEY the demo still works using a fallback response.
For production add admin authentication, database persistence, rate limiting,
origin allowlists, HTTPS, and tenant ownership controls.
