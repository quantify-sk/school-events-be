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


# Kultúra pre školy - Projektová dokumentácia

## Použité technológie

## Použité technológie

- **Backend**: [FastAPI (Python)][8]
  - Moderný, vysokovýkonný framework pre budovanie API s Pythonom, založený na štandardných typových hintoch.
- **Databáza**: [PostgreSQL][5]
  - Relačná databáza s vysokou výkonom a flexibilitou.
- **Caching**: [Redis][10]
  - Rýchly a flexibilný caching systém.
- **Task Queue**: [Celery][10]
  - Distribuovaný systém na spracovanie úloh v reálnom čase.
- **Reverse Proxy**: [Caddy][1]
  - Silný a rozširovateľný server pre službu webových stránok a aplikácií.
- **Kontajnerizácia**: [Docker a Docker Compose][11]
  - Kontajnerizácia aplikácií pomocou Dockeru a správa kontajnerov pomocou Docker Compose.
- **Dependency Management**: [Poetry][9]
  - Nástroj pre správu závislostí a balíkov v Python projektoch.

## Požiadavky

- Docker a Docker Compose
- Make
- Git

Príkazy v tejto dokumentácii môžete prispôsobiť v **Makefile**. Môžete ich spustiť s alebo bez Dockeru.

## Inštalácia a spustenie projektu

1. Naklonujte repozitár
```bash
   git clone [URL_REPOZITÁRA]
   cd [NÁZOV_PROJEKTU]
```

2. Najprv sa uistite, že máte nainštalované všetky balíky.

```bash
make install
```

3. Spustite vývojové prostredie: 
Spustiť lokálne v dev móde:
```bash
   make run-dev-build
```
Spustiť lokálne v production móde(AutoReload vypnutý):
```bash
   make run-prod-build
```

4. Naplňte databázu počiatočnými dátami:
```bash
   make seed-db
```

5.(Voliteľné) Pre prípad, že potrebujete kompletne resetnúť aplikáciu:
```bash
   make rm-volumes
```
Následne opakujte spustenie apikácie znova

## Po spustení je backend dostupný na:
- API: [http://localhost:8082/api/v1](http://localhost:8002/api/v1) 
Swagger dokumentácia: [http://localhost:8082/api/docs](http://localhost:8002/api/docs) 

# Poznámky
- Projekt je nakonfigurovaný tak, aby fungoval s    predvolenými hodnotami. Vo väčšine prípadov nie je potrebné manuálne vytvárať .env súbor.
- Ak potrebujete upraviť konfiguráciu (napríklad pre produkčné nasadenie), vytvorte .env súbor s požadovanými hodnotami.
- Uistite sa, že máte nainštalované všetky potrebné nástroje (Docker, Docker Compose, Make) pred spustením projektu.
- V prípade problémov skontrolujte logy pomocou make logs-dev alebo make logs-prod.