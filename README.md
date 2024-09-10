# Kultúra pre školy - Projektová dokumentácia

## Použité technológie

- **Backend**: [FastAPI (Python)](https://fastapi.tiangolo.com)
  - Moderný, vysokovýkonný framework pre budovanie API s Pythonom, založený na štandardných typových hintoch.
- **Databáza**: [PostgreSQL](https://www.postgresql.org/docs/)
  - Relačná databáza s vysokou výkonom a flexibilitou.
- **Caching**: [Redis](https://redis.io/docs/latest/)
  - Rýchly a flexibilný caching systém.
- **Task Queue**: [Celery](https://docs.celeryq.dev/en/stable/#)
  - Distribuovaný systém na spracovanie úloh v reálnom čase.
- **Reverse Proxy**: [Caddy](https://caddyserver.com/docs/)
  - Silný a rozširovateľný server pre službu webových stránok a aplikácií.
- **Kontajnerizácia**: [Docker a Docker Compose](https://docs.docker.com/compose/)
  - Kontajnerizácia aplikácií pomocou Dockeru a správa kontajnerov pomocou Docker Compose.
- **Dependency Management**: [Poetry](https://python-poetry.org/docs/)
  - Nástroj pre správu závislostí a balíkov v Python projektoch.

## Požiadavky

- Docker a Docker Compose
- Make
- Git

Príkazy v tejto dokumentácii môžete prispôsobiť v **Makefile**. Môžete ich spustiť s alebo bez Dockeru.

## Inštalácia a spustenie projektu

1. Naklonujte repozitár
```bash
git clone https://github.com/quantify-sk/school-events-be.git
cd school-events-be
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
make run-prod
```

4. Naplňte databázu počiatočnými dátami:
```bash
make seed-db
```

5. (Voliteľné) Pre prípad, že potrebujete kompletne resetnúť aplikáciu:
```bash
make rm-volumes
```
Následne opakujte spustenie apikácie znova

## Po spustení je backend dostupný na:
- API: [http://localhost:8082/api/v1](http://localhost:8002/api/v1) 
- Swagger dokumentácia: [http://localhost:8082/api/docs](http://localhost:8002/api/docs) 

# Poznámky
- Projekt je nakonfigurovaný tak, aby fungoval s    predvolenými hodnotami. Vo väčšine prípadov nie je potrebné manuálne vytvárať .env súbor.
- Ak potrebujete upraviť konfiguráciu (napríklad pre produkčné nasadenie), vytvorte .env súbor s požadovanými hodnotami.
- Uistite sa, že máte nainštalované všetky potrebné nástroje (Docker, Docker Compose, Make) pred spustením projektu.
- V prípade problémov skontrolujte logy pomocou 
```bash
make logs-dev
``` 
alebo

```bash
make logs-prod
``` 