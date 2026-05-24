.PHONY: help sync sync-backend sync-frontend env models backend frontend dev load-models

help:
	@echo "Available commands:"
	@echo "  make sync          - Install both backend (uv) and frontend (npm) dependencies"
	@echo "  make sync-backend  - Install Python dependencies using uv"
	@echo "  make sync-frontend - Install Node dependencies using npm"
	@echo "  make env           - Copy .env.example to .env"
	@echo "  make models        - Pull the required Ollama models"
	@echo "  make backend       - Run the FastAPI backend server"
	@echo "  make frontend      - Run the frontend development server"
	@echo "  make dev           - Run both backend and frontend (opens backend in new window)"

# Install ALL dependencies (backend and frontend)
sync: sync-backend sync-frontend

# Install Python dependencies using uv
sync-backend:
	uv sync

# Install Node dependencies for the frontend
sync-frontend:
	cd frontend && npm install

# Set up the .env file from the example
env:
	cp .env.example .env
	@echo "Created .env file. Please open it and update the secret keys."

# Pull required models for Ollama
# Ensure the Ollama app is installed and running before executing this
models:
	ollama pull llama3.1:8b
	ollama pull shieldgemma:2b

# Pre-load both models into memory (keeps them alive indefinitely)
load_models:
	@echo "Pre-loading ShieldGemma and LLaMA 3.1 into Ollama..."
	python -c "import urllib.request; urllib.request.urlopen(urllib.request.Request('http://localhost:11434/api/generate', data=b'{\"model\":\"shieldgemma:2b\",\"keep_alive\":-1}'))"
	python -c "import urllib.request; urllib.request.urlopen(urllib.request.Request('http://localhost:11434/api/generate', data=b'{\"model\":\"llama3.1:8b-instruct-q4_K_M\",\"keep_alive\":-1}'))"

# Run the FastAPI backend server
backend: load_models
	uvicorn app.main:app --reload

# Run the frontend development server
frontend:
	cd frontend && npm run dev

# Run both backend and frontend concurrently
dev:
	start uvicorn app.main:app --reload
	cd frontend && npm run dev