install:
	uv sync --locked

docker-build:
	docker build -t mnemovox -f Dockerfile .

docker-run: docker-build
	docker-compose up

