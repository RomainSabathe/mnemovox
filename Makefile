install:
	uv sync --locked --extra dev
	uv run pre-commit install

docker-build:
	docker build -t mnemovox -f Dockerfile .

docker-run: docker-build
	docker-compose up

