# Project settings
PROJECT_NAME := regserver
IMAGE_NAME   := regserver:latest
COMPOSE      := docker compose

VENV         ?= .validate_venv
PY           := $(VENV)/bin/python
PIP          := $(VENV)/bin/pip3
BEHAVE       := $(VENV)/bin/behave

REQ_DEV      ?= requirements-dev.txt

WAIT_SCRIPT  := src/dump1090curses/wait-for-regserver-health.sh
BASE_URL     := http://localhost:5001/
CHECK_URL    := $(BASE_URL)/health

# Default target
.DEFAULT_GOAL := help

## Build the Docker image
build:
	@echo "▶ Building $(IMAGE_NAME)"
	DOCKER_BUILDKIT=1 $(COMPOSE) build

## Start the service (build if needed)
up:
	@echo "▶ Starting $(PROJECT_NAME)"
	$(COMPOSE) up -d

## Stop the service
down:
	@echo "▶ Stopping $(PROJECT_NAME)"
	$(COMPOSE) down

## Restart the service
restart: down up

### Rebuild
rebuild: down build up

## Tail logs
logs:
	$(COMPOSE) logs -f $(PROJECT_NAME)

## Show running containers
ps:
	$(COMPOSE) ps

## Open a shell inside the running container
shell:
	$(COMPOSE) exec $(PROJECT_NAME) sh

## Run health check manually
health:
	@echo "▶ Checking health"
	curl -fsS http://localhost:5001/health || echo "❌ Health check failed"


# Ensure virtualenv exists and has requirements installed
.PHONY: venv-ensure
venv-ensure:
	@if [ ! -d "$(VENV)" ]; then \
	  echo "▶ Creating virtualenv at $(VENV)..."; \
	  python3 -m venv $(VENV); \
	  $(PIP) install --upgrade pip setuptools wheel; \
	else \
	  echo "▶ Virtualenv $(VENV) exists"; \
	fi
	@echo "▶ Installing dev requirements from $(REQ_DEV)..."
	@$(PIP) install --upgrade -r $(REQ_DEV)

.PHONY: wait 
wait:
	@echo "▶ Waiting for regserver health"
	@WAIT_URL=$(BASE_URL) $(WAIT_SCRIPT) -u $(CHECK_URL) -t 60 -i 2

.PHONY: test-behave
test-behave:
	@echo "▶ Running behave against $(BASE_URL)"
	$(BEHAVE) -D base_url="$(BASE_URL)"

.PHONY: validate
validate: up wait venv-ensure test-behave
	@echo "▶ Validating a successful build/deploy"
	

.PHONY: deploy
deploy: build validate

## Remove containers, images, and volumes (⚠ destructive)
.PHONY: clean
clean:
	@echo "⚠ Removing containers, images, and volumes"
	$(COMPOSE) down -v --rmi all --remove-orphans

## Remove dangling Docker resources (global)
.PHONY: prune
prune:
	@echo "⚠ Pruning unused Docker resources"
	docker system prune -f

## Show help
help:
	@echo ""
	@echo "Available targets:"
	@echo "  make build       Build Docker image"
	@echo "  make up          Start service"
	@echo "  make down        Stop service"
	@echo "  make restart     Restart service"
	@echo "  make rebuild     Rebuild service (inc. up)"
	@echo "  make logs        Tail logs"
	@echo "  make ps          Show service status"
	@echo "  make shell       Shell into container"
	@echo "  make health      Run health check"
	@echo "  make clean       Remove containers/images/volumes"
	@echo "  make prune       Docker system prune"
	@echo "  make test-behave Run behave validation"
	@echo "  make validate    Test correct API behaviour"
	@echo "  make deploy      Build and Validate"
	@echo "  make wait        Ensure healthcheck is running"
	@echo ""

