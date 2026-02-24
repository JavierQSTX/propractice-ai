generate-requirements:
	poetry export -f requirements.txt --without-hashes | awk -F ";" '{print $$1}' > requirements.txt


build: generate-requirements
	docker build . -t propractice-ai:local

start-server: build
	docker run \
		--env-file .env \
		-p 8080:8080 \
		propractice-ai:local

send-request:
	poetry run python ./scripts/send_request.py

deploy: generate-requirements
	./scripts/deploy.sh

deploy-dev: generate-requirements
	./scripts/deploy-dev.sh
