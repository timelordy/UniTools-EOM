 .PHONY: lint test check install-dev clean
 
 # Install development dependencies
 install-dev:
 	pip install -r requirements-dev.txt
 
 # Run flake8 linting
 lint:
 	flake8 EOMTemplateTools.extension/lib/ tests/
 
 # Run pytest
 test:
 	pytest tests/ -v
 
 # Run tests with coverage
 test-cov:
 	pytest tests/ --cov=EOMTemplateTools.extension/lib --cov-report=term-missing
 
 # Run all checks (lint + test)
 check: lint test
 
 # Install pre-commit hooks
 install-hooks:
 	pre-commit install
 
 # Run pre-commit on all files
 pre-commit:
 	pre-commit run --all-files
 
 # Clean cache files
 clean:
 	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
 	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
 	find . -type f -name "*.pyc" -delete 2>/dev/null || true
