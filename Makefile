staging-b:
	docker compose -f docker-compose.yml -f docker-compose.staging.yml up --build
staging:
	docker compose -f docker-compose.yml -f docker-compose.staging.yml up
prod-b:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build
prod:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up