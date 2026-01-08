# Docker Development Skill

## Description
Docker development environment setup and management for Item Management System.

## Trigger Phrases
- "docker setup"
- "container dev"
- "local dev env"
- "docker development"

## When to Use
When you need to:
- Set up local development environment with Docker
- Build Docker images
- Run containers
- Debug container issues
- Configure Docker Compose
- Manage volumes and networks
- Set up database containers
- Access container logs

## Available Tools
- Bash (for Docker commands)
- Docker MCP (if available)
- Read/Write (for Dockerfile/docker-compose.yml)
- Grep (for finding Docker config)

## MUST DO
1. Check existing Docker configuration files
2. Use Docker Compose for multi-container setup
3. Follow Docker best practices:
   - Use specific version tags (not `latest`)
   - Minimize image layers
   - Use .dockerignore to exclude unnecessary files
   - Set proper resource limits
   - Use non-root user in containers
4. Document all port mappings
5. Configure environment variables properly
6. Set up volume persistence for data
7. Configure health checks
8. Ensure proper networking between containers

## MUST NOT DO
- Do NOT use `latest` tag in production
- Do NOT run containers as root (unless necessary)
- Do NOT commit secrets to images
- Do NOT ignore container logs
- Do NOT skip volume configuration for data persistence
- Do NOT expose unnecessary ports
- Do NOT ignore health checks

## Context
- Project uses Docker and Docker Compose
- Existing files:
  - `Dockerfile` - Application image
  - `docker-compose.yml` - Multi-container orchestration
  - `.dockerignore` - Files to exclude
- Services:
  - Web application (Flask)
  - PostgreSQL database
  - MongoDB database (optional)
  - Redis (optional, for caching)
- Application runs on port 8080

## Docker Compose Structure

```yaml
version: '3.8'

services:
  # Flask Application
  web:
    build: .
    ports:
      - "8080:5000"
    environment:
      - FLASK_ENV=development
      - DB_TYPE=postgres
      - DATABASE_URL=postgresql://user:password@db:5432/itemman
    volumes:
      - ./app:/app/app
      - ./static:/app/static
      - ./uploads:/app/uploads
    depends_on:
      db:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # PostgreSQL Database
  db:
    image: postgres:16-alpine
    environment:
      - POSTGRES_DB=itemman
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d itemman"]
      interval: 10s
      timeout: 5s
      retries: 5

  # MongoDB (optional)
  mongo:
    image: mongo:7
    environment:
      - MONGO_INITDB_DATABASE=myDB
    volumes:
      - mongo_data:/data/db
    ports:
      - "27017:27017"

volumes:
  postgres_data:
  mongo_data:
```

## Common Docker Commands

### Development
```bash
# Build and start all containers
docker compose up --build

# Start in detached mode
docker compose up -d

# View logs
docker compose logs -f

# Stop all containers
docker compose down

# Stop and remove volumes
docker compose down -v
```

### Building
```bash
# Build specific service
docker compose build web

# Rebuild without cache
docker compose build --no-cache

# Build with build arguments
docker compose build --build-arg ENV=production
```

### Container Management
```bash
# List running containers
docker ps

# List all containers (including stopped)
docker ps -a

# View container logs
docker logs <container_id>

# Execute command in container
docker exec -it <container_id> /bin/bash

# Copy files to/from container
docker cp local_file.txt <container_id>:/app/
docker cp <container_id>:/app/remote_file.txt ./
```

### Debugging
```bash
# View container logs in real-time
docker compose logs -f web

# Inspect container details
docker inspect <container_id>

# Check container resource usage
docker stats

# Access container shell for debugging
docker compose exec web /bin/bash
```

## Dockerfile Best Practices

### Multi-stage Build
```dockerfile
# Build stage
FROM python:3.13-slim as builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.13-slim

WORKDIR /app

COPY --from=builder /root/.local /root/.local
COPY --from=builder /app/requirements.txt .
COPY . .

RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 5000
CMD ["python", "run.py"]
```

### Optimize Layers
```dockerfile
# Good: Fewer layers
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client && \
    rm -rf /var/lib/apt/lists/*

# Bad: Multiple layers
RUN apt-get update
RUN apt-get install -y gcc
RUN apt-get install -y postgresql-client
RUN rm -rf /var/lib/apt/lists/*
```

## Environment Configuration

### Development
```bash
# .env.dev
FLASK_ENV=development
FLASK_DEBUG=1
DB_TYPE=postgres
DATABASE_URL=postgresql://dev:devpass@db:5432/itemman
```

### Production
```bash
# .env.prod
FLASK_ENV=production
FLASK_DEBUG=0
DB_TYPE=postgres
DATABASE_URL=postgresql://prod:${DB_PASSWORD}@db:5432/itemman
MAIL_SERVER=${SMTP_SERVER}
MAIL_PORT=${SMTP_PORT}
MAIL_USERNAME=${SMTP_USER}
MAIL_PASSWORD=${SMTP_PASSWORD}
```

## Troubleshooting

### Container Won't Start
```bash
# Check logs
docker compose logs web

# Check if port is in use
lsof -i :8080

# Rebuild without cache
docker compose build --no-cache web
```

### Database Connection Issues
```bash
# Check if database is running
docker compose ps db

# Check database logs
docker compose logs db

# Test connection
docker compose exec db psql -U user -d itemman
```

### Volume Permission Issues
```bash
# Fix volume permissions on host
sudo chown -R $USER:$USER ./data

# Or run container as current user
docker compose run --rm web id
```

## Performance Tuning

### Resource Limits
```yaml
services:
  web:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
```

### Database Optimization
```yaml
db:
  command:
    - postgres
    - -c
    - shared_buffers=256MB
    - -c
    - max_connections=100
```

## Docker Development Checklist
- [ ] Docker Compose configuration complete
- [ ] All services start successfully
- [ ] Database accessible from application
- [ ] Volumes properly mounted
- [ ] Environment variables configured
- [ ] Health checks passing
- [ ] Application accessible via browser
- [ ] Logs are readable
- [ ] Hot reloading works in development
- [ ] Production build works correctly
