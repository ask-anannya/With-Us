dev:
	cd backend && .venv/Scripts/uvicorn app.main:app --reload --port 8787 & cd frontend && npm run dev

seed:
	cd backend && .venv/Scripts/python -m app.seed

test:
	cd backend && .venv/Scripts/python -m pytest -q

leak:
	cd backend && .venv/Scripts/python scripts/leak_eval.py
