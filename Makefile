# Project settings
PROJECT_NAME := regserver
IMAGE_NAME   := regserver:latest
COMPOSE      := docker compose

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

## Remove containers, images, and volumes (⚠ destructive)
clean:
	@echo "⚠ Removing containers, images, and volumes"
	$(COMPOSE) down -v --rmi all --remove-orphans

## Remove dangling Docker resources (global)
prune:
	@echo "⚠ Pruning unused Docker resources"
	docker system prune -f

## Show help
help:
	@echo ""
	@echo "Available targets:"
	@echo "  make build     Build Docker image"
	@echo "  make up        Start service"
	@echo "  make down      Stop service"
	@echo "  make restart   Restart service"
	@echo "  make logs      Tail logs"
	@echo "  make ps        Show service status"
	@echo "  make shell     Shell into container"
	@echo "  make health    Run health check"
	@echo "  make clean     Remove containers/images/volumes"
	@echo "  make prune     Docker system prune"
	@echo ""

