local:
	docker compose up
local-ub:
	docker compose up --build
local-b:
	docker compose build
local-bnc:
	docker compose build --no-cache

staging:
	docker compose -f docker-compose.yml -f docker-compose.staging.yml up
staging-ub:
	docker compose -f docker-compose.yml -f docker-compose.staging.yml up --build
staging-b:
	docker compose -f docker-compose.yml -f docker-compose.staging.yml build
staging-bnc:
	docker compose -f docker-compose.yml -f docker-compose.staging.yml build --no-cache

prod:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up
prod-ub:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build
prod-b:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml build
prod-bnc:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml build --no-cache