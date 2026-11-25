# Karmathy HCM — Makefile

.PHONY: seed-demo seed-reset test lint

# Run the deterministic synthetic seed against a local SQLite database.
seed-demo:
	@echo "==> Seeding synthetic demo data (local SQLite)..."
	@rm -f seed_dev.db
	SECRET_KEY="local-test-secret-key-not-for-production-0123456789" \
	DATABASE_URL="sqlite:///./seed_dev.db" \
	python -m seed.dev.seed_dev

# Drop the seed database and reseed from scratch.
seed-reset:
	@rm -f seed_dev.db
	$(MAKE) seed-demo

# Run all backend test suites.
test:
	bash ci/run_backend_tests.sh

# Run the secret scan.
lint:
	python ci/secret_scan.py
