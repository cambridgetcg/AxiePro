# AxiePro Backend - Testing Makefile
# ====================================

.PHONY: help test test-unit test-integration test-e2e test-cov test-fast lint clean

# Default target
help:
	@echo "AxiePro Backend Test Commands"
	@echo "=============================="
	@echo ""
	@echo "Test Commands:"
	@echo "  make test              - Run all tests"
	@echo "  make test-unit         - Run unit tests only (fast)"
	@echo "  make test-integration  - Run integration tests only"
	@echo "  make test-e2e          - Run E2E tests only"
	@echo "  make test-fast         - Run unit tests with fail-fast"
	@echo ""
	@echo "Coverage Commands:"
	@echo "  make test-cov          - Run all tests with coverage report"
	@echo "  make test-cov-html     - Run tests with HTML coverage report"
	@echo "  make test-cov-unit     - Unit tests with coverage"
	@echo "  make test-cov-int      - Integration tests with coverage"
	@echo ""
	@echo "Quality Commands:"
	@echo "  make lint              - Run linting (ruff + black check)"
	@echo "  make format            - Format code with black"
	@echo "  make typecheck         - Run type checking with mypy"
	@echo ""
	@echo "Utility Commands:"
	@echo "  make clean             - Remove cache and coverage files"
	@echo "  make install-test      - Install test dependencies"

# =============================================================================
# Test Execution
# =============================================================================

# Run all tests
test:
	pytest tests/ -v

# Run unit tests only (fastest - 70% of test pyramid)
test-unit:
	pytest tests/unit/ -v

# Run integration tests only (25% of test pyramid)
test-integration:
	pytest tests/integration/ -v

# Run E2E tests only (5% of test pyramid - slowest)
test-e2e:
	pytest tests/e2e/ -v

# Run unit tests with fail-fast (stop on first failure)
test-fast:
	pytest tests/unit/ -v -x

# Run tests matching a pattern
test-match:
	@read -p "Test pattern: " pattern; \
	pytest tests/ -v -k "$$pattern"

# =============================================================================
# Coverage Reporting
# =============================================================================

# Run all tests with coverage
test-cov:
	pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=xml

# Run tests with HTML coverage report
test-cov-html:
	pytest tests/ -v --cov=src --cov-report=html --cov-report=term-missing
	@echo ""
	@echo "Coverage report generated: htmlcov/index.html"

# Unit tests with coverage
test-cov-unit:
	pytest tests/unit/ -v --cov=src --cov-report=term-missing

# Integration tests with coverage
test-cov-int:
	pytest tests/integration/ -v --cov=src --cov-report=term-missing

# E2E tests with coverage
test-cov-e2e:
	pytest tests/e2e/ -v --cov=src --cov-report=term-missing

# Coverage with minimum threshold enforcement
test-cov-check:
	pytest tests/ -v --cov=src --cov-report=term-missing --cov-fail-under=70

# =============================================================================
# Code Quality
# =============================================================================

# Run linting
lint:
	ruff check src/ tests/
	black --check src/ tests/

# Format code
format:
	black src/ tests/
	ruff check --fix src/ tests/

# Type checking
typecheck:
	mypy src/ --ignore-missing-imports

# =============================================================================
# Utilities
# =============================================================================

# Clean up cache and coverage files
clean:
	rm -rf .pytest_cache
	rm -rf __pycache__
	rm -rf tests/__pycache__
	rm -rf tests/unit/__pycache__
	rm -rf tests/integration/__pycache__
	rm -rf tests/e2e/__pycache__
	rm -rf tests/mocks/__pycache__
	rm -rf tests/factories/__pycache__
	rm -rf .coverage
	rm -rf htmlcov
	rm -rf coverage.xml
	rm -rf .ruff_cache
	rm -rf .mypy_cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Install test dependencies
install-test:
	pip install pytest pytest-asyncio pytest-cov httpx respx fakeredis factory-boy

# =============================================================================
# CI/CD Targets
# =============================================================================

# CI test run (all tests with coverage, XML output for CI)
ci-test:
	pytest tests/ -v --cov=src --cov-report=xml --cov-report=term-missing --junitxml=test-results.xml

# Quick CI check (unit tests only, faster)
ci-quick:
	pytest tests/unit/ -v --cov=src --cov-report=xml --junitxml=test-results.xml
