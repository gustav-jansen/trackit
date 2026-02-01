.PHONY: test

test:
	uv run --extra test pytest tests/
