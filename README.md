# School Events API

### Getting Started

The commands in this documentation can be customized in the **Makefile**. They can be executed with or without Docker.

This project uses Poetry. If you don't have it installed, you can follow the instructions in the [Poetry Documentation](https://python-poetry.org/docs/#installation).

- Run the server (Recommended using Docker) or for fresh init:

```bash
# Remove existing containers
make rm-volumes
# Run locally with Docker in dev mode and force build
make run-dev-build
# or
# Run locally with Docker in dev mode
make run-dev
# Seed database
make seed-db
# or
# Run locally with Docker in prod mode (Autoreload disabled)
make run-prod
```

Open [http://fastapi.localhost/docs](http://fastapi.localhost/docs) with your browser to see the result.

- Run the server without Docker:

First, make sure you have all packages installed:

```bash
make install
```

```bash
make run-app
```

Open [http://localhost:8000/docs](http://localhost:8002/docs) with your browser to see the result.
