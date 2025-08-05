.PHONY: ruff test clean install dev-install

# Default target
all: ruff test

# Run Ruff linter and formatter
ruff:
	-ruff check --fix .
	ruff format .

# Run tests with pytest
test:
	pytest

# Run tests with coverage
coverage:
	pytest --cov=src/stoppls --cov-report=term-missing

# Clean up Python cache files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name "*.egg" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".coverage" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name "dist" -exec rm -rf {} +
	find . -type d -name "build" -exec rm -rf {} +

# Install the package
install:
	uv pip install .

# Install the package in development mode
dev-install:
	uv pip install -e .

# Install development dependencies
dev-deps:
	uv pip install -r requirements.txt

# Help command
help:
	@echo "Available commands:"
	@echo "  make ruff         - Run Ruff linter and formatter"
	@echo "  make test         - Run tests with pytest"
	@echo "  make coverage     - Run tests with coverage report"
	@echo "  make clean        - Clean up Python cache files"
	@echo "  make install      - Install the package"
	@echo "  make dev-install  - Install the package in development mode"
	@echo "  make dev-deps     - Install development dependencies"
	@echo "  make all          - Run ruff and tests (default)"
	@echo "  make help         - Show this help message"