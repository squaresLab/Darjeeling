.PHONY: all check install test lint

all: install check

lint:
	poetry run ruff check src
	poetry run mypy src

test:
	poetry run pytest

install:
	poetry install --with dev

check: lint test
