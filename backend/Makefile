PACKAGES = -e packages/core -e packages/ingest -e packages/retrieval -e packages/storage -e packages/explain -e packages/templates \
           -e adapters/http-api -e adapters/mcp-server -e adapters/worker -e app

.PHONY: install test check docker-build docker-check docker-test

install:
	pip install $(PACKAGES) pytest

test:
	pytest packages/core/tests packages/templates/tests app/tests tests

check:
	python -m glosa_app check

docker-build:
	docker build -t glosa:dev --target runtime .

docker-check:
	docker compose up --build check

docker-test:
	docker compose --profile test run --rm --build tests
