.PHONY: install test build start docker-build docker-up docker-down clean

install:
	cd backend && python -m pip install -r requirements.txt
	cd frontend && npm ci

test:
	python -m unittest discover -s backend/tests
	python -m compileall -q backend/app

build:
	cd frontend && npm run build

start:
	docker compose up --build

docker-build:
	docker compose build

docker-up:
	docker compose up --build

docker-down:
	docker compose down

clean:
	cd frontend && rm -rf .next
	find backend -type d -name __pycache__ -prune -exec rm -rf {} +
