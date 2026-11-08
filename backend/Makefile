PACKAGES = -e packages/core -e packages/ingest -e packages/retrieval -e packages/storage -e packages/explain -e packages/templates \
           -e adapters/http-api -e adapters/mcp-server -e adapters/worker -e app

.PHONY: install test test-memory test-sqlite check docker-build docker-check docker-test

install:
	pip install $(PACKAGES) pytest

test: test-memory test-sqlite

# Toda la batería con los dobles en memoria
test-memory:
	pytest packages/core/tests packages/explain/tests packages/ingest/tests packages/storage/tests packages/templates/tests adapters/worker/tests app/tests tests

# Las mismas pruebas de core (incluidas las 14 obligatorias) contra los adaptadores SQLite reales
test-sqlite:
	GLOSA_TEST_ADAPTERS=glosa_storage.testing:make_adapters pytest packages/core/tests

check:
	python -m glosa_app check

docker-build:
	docker build -t glosa:dev --target runtime .

docker-check:
	docker compose up --build check

docker-test:
	docker compose --profile test run --rm --build tests
