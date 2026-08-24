# Online Cinema API

Online Cinema API is a REST API built with FastAPI for user authentication, profiles, movie management, and personalized favorite movies.

The project demonstrates asynchronous backend development, JWT authentication, role-based access control, background tasks, S3-compatible storage, Dockerized environments, and automated testing.

## Table of Contents

- [Features](#features)
  - [Authentication](#authentication)
  - [Roles and Permissions](#roles-and-permissions)
  - [User Profiles](#user-profiles)
  - [Movies](#movies)
  - [Favorites](#favorites)
  - [Background Services](#background-services)
  - [API Documentation](#api-documentation)
  - [Testing](#testing)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Setup](#setup)
- [Run Development](#run-development)
  - [Requirements](#requirements)
  - [Environment](#environment)
  - [Start](#start)
  - [Testing](#testing-1)
- [Run Production-like Environment](#run-production-like-environment)
  - [Requirements](#requirements-1)
  - [Environment](#environment-1)
  - [Start](#start-1)
- [Database Migrations](#database-migrations)
- [API Documentation](#api-documentation-1)

## Features

### Authentication

- User registration with email activation
- JWT access and refresh tokens
- Password change and password reset
- Resending expired activation links
- Password complexity validation
- Expired token cleanup with Celery Beat

### Roles and Permissions

The API supports three roles:

- `USER`
- `MODERATOR`
- `ADMIN`

Movie management endpoints are protected with role-based access control.

### User Profiles

- Personal user profiles
- Avatar upload to S3-compatible storage
- Profile data validation
- Favorite movies included in profile responses

### Movies

- Movie catalog with pagination
- Movie details
- Moderator-protected CRUD operations
- Genres, actors, languages, and countries
- Movie data validation and duplicate protection

### Favorites

- Add movies to favorites
- Remove movies from favorites
- Favorite movies linked to user profiles

### Background Services

- Celery for background tasks
- Celery Beat for scheduled tasks
- Redis as the message broker
- Mailpit for development email testing
- MinIO for development object storage

### API Documentation

- OpenAPI / Swagger documentation
- Swagger UI available at `/docs`
- Documentation protected with HTTP Basic authentication

### Testing

Automated tests cover authentication, profiles, permissions, movie operations, pagination, favorites, validation, and database interactions.

## Tech Stack

- **Python 3.12**
- **FastAPI**
- **SQLAlchemy 2.0** with async support
- **PostgreSQL**
- **Alembic**
- **Pydantic**
- **PyJWT**
- **Celery**
- **Redis**
- **MinIO / S3-compatible storage**
- **Mailpit**
- **Docker & Docker Compose**
- **Poetry**
- **Pytest**

## Architecture

The project follows a layered architecture:

- **Routes** handle HTTP requests and dependencies
- **Services** contain business logic
- **Repositories** handle database operations
- **Schemas** define request and response validation
- **Models** define database entities and relationships
- **Integrations** handle external services such as email and S3-compatible storage

The application uses asynchronous SQLAlchemy sessions for database access and dependency injection provided by FastAPI.

## Project Structure

The project follows a layered architecture that separates API routes, business logic, database operations, validation, and external integrations.

```text
online_cinema_api/
├── alembic/                 # Database migrations
├── app/
│   ├── core/                # Application configuration and security
│   ├── models/              # SQLAlchemy database models
│   ├── notifications/       # Email notification logic
│   ├── repositories/        # Database access layer
│   ├── routes/              # FastAPI endpoints
│   ├── schemas/             # Pydantic request and response schemas
│   ├── services/            # Business logic
│   ├── storages/            # S3-compatible storage integration
│   ├── tasks/               # Celery background tasks
│   ├── tests/               # Automated tests
│   ├── validators/          # Custom validation logic
│   ├── database.py          # Database configuration
│   ├── dependencies.py      # Shared FastAPI dependencies
│   ├── exceptions.py        # Application exceptions
│   └── main.py              # FastAPI application entry point
├── .env.example             # Development environment example
├── .env.prod.example        # Production environment example
├── alembic.ini              # Alembic configuration
├── docker-compose.dev.yml   # Development Docker environment
├── docker-compose.prod.yml  # Production-like Docker environment
├── Dockerfile               # Development Docker image
├── Dockerfile.prod          # Production Docker image
├── poetry.lock
├── pyproject.toml
└── README.md
```

## Setup

Clone the repository:

```bash
git clone https://github.com/idubina/online-cinema-api.git
cd online_cinema_api
```

If you want to run project commands locally with Poetry, install the dependencies:

```bash
poetry install
```

For Docker-based development, local Python installation is not required.

## Run Development

Running the development environment starts the complete local setup required for development and testing. It includes the API with hot reload and local versions of all supporting services, so no external SMTP or object storage services are required.

### Requirements

- Docker
- Docker Compose

### Environment

Create the development environment file:

```bash
cp .env.example .env
```

The development environment includes PostgreSQL, Redis, Celery Worker and Celery Beat, Mailpit for email testing, MinIO for object storage, and a separate test database.

### Start

Build and start the development environment:

```bash
docker compose -f docker-compose.dev.yml up --build
```

The API and Swagger documentation will be available at:

```text
http://localhost:8000
http://localhost:8000/docs
```

Additional development services:

```text
Mailpit:       http://localhost:8025
MinIO Console: http://localhost:9001
```

Stop the environment:

```bash
docker compose -f docker-compose.dev.yml down
```

### Testing

The project can be tested locally using Poetry:

```bash
poetry run pytest
```

or inside Docker using the dedicated test service:

```bash
docker compose -f docker-compose.dev.yml --profile test run --rm tests
```

Test coverage can be checked with:

```bash
poetry run pytest --cov=app --cov-report=term-missing
```

Current test coverage is approximately **86%**.

## Run Production-like Environment

The production-like environment provides a configuration closer to a real deployment. It runs the application without hot reload, test services, Mailpit, or local MinIO and expects production services such as SMTP and S3-compatible storage to be configured externally.

This configuration can be used as a base for deployment after providing the required production environment variables.

### Requirements

- Docker
- Docker Compose
- SMTP provider credentials
- S3-compatible storage credentials

### Environment

Create the production environment file:

```bash
cp .env.prod.example .env.prod
```

Configure the required values in `.env.prod`, including:

- PostgreSQL credentials
- JWT secrets
- API documentation credentials
- SMTP credentials
- S3-compatible storage credentials

### Start

Build and start the production-like environment:

```bash
docker compose \
  --env-file .env.prod \
  -f docker-compose.prod.yml \
  up -d --build
```

The production-like environment runs FastAPI, PostgreSQL, Redis, Celery Worker, Celery Beat, and automatic Alembic migrations.

Check running services:

```bash
docker compose \
  --env-file .env.prod \
  -f docker-compose.prod.yml \
  ps
```

Stop the environment:

```bash
docker compose \
  --env-file .env.prod \
  -f docker-compose.prod.yml \
  down
```

## Database Migrations

Database migrations are managed with Alembic.

Apply all existing migrations:

```bash
poetry run alembic upgrade head
```

Create a new migration after changing database models:

```bash
poetry run alembic revision --autogenerate -m "migration description"
```

When using Docker, migrations are applied automatically by the dedicated `migrator` service before the API starts.

## API Documentation

Interactive API documentation is available through Swagger UI:

```text
http://localhost:8000/docs
```

Access to the documentation is protected with HTTP Basic authentication using credentials configured in the environment:

```env
DOCS_USER=
DOCS_PASSWORD=
```

Swagger UI provides request schemas, response schemas, endpoint summaries, and the ability to test API endpoints directly from the browser.

The OpenAPI schema is available at:

```text
http://localhost:8000/openapi.json
```

Both Swagger UI and the OpenAPI schema require documentation credentials.

## Author

Illia Dubina  
GitHub: [idubina](https://github.com/idubina)