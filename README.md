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

# Požiadavky

Pred začiatkom sa uistit, že máte nainštalované nasledujúce:

1. Git
```bash
sudo apt update
sudo apt install -y git
git clone https://github.com/quantify-sk/school-events-be.git
cd school-events-be
```

2. Python 3.11
```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update

sudo apt install -y python3 python3-pip python3.11-venv python3.11-dev
sudo apt install libpq-dev python3-dev gcc
```
3. Docker a docker Compose
```bash
sudo apt-get update
sudo apt-get install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update

sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```
4. Curl pre inštaláciu poetry
```bash
sudo apt install -y curl
```

# Klonovanie repozitára
Naklonujte repozitár
```bash
git clone GIT-URL
cd school-events-be
```

# Pridat environmentálne premenné

Pridaj premenné pre váš SMTP server, email administrátora a ID administrátora do .env.
```
# Email
MAIL_USERNAME="example@example.com"
MAIL_PASSWORD="securepassword123"
MAIL_FROM="noreply@example.sk"
MAIL_SERVER="smtp.example.sk"
MAIL_PORT=587
MAIL_FROM_NAME="Example name"
SENDING_NOTIFICATIONS="True/False"
ADMIN_EMAIL="admin@example.sk"
ADMIN_ID=12345
```


## Spustenie projektu bez Dockeru

1. Inštalácia Poetry
```bash
curl -sSL https://install.python-poetry.org | python3 -
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```
2. Inštalácia závislostí: Uistite sa, že sú nainštalované vývojové hlavičky PostgreSQL:
```bash
sudo apt install -y libpq-dev
```

Potom nainštalujte závislosti projektu
```bash
make install
```
Ak narazíte na chyby s psycopg2, použite namiesto toho binárnu verziu:
```bash
poetry add psycopg2-binary
```

3. Spustenie aplikácie
```bash
make run-app
```

## Spustenie projektu pomocou Dockeru


1. Vytvorenie a spustenie kontajnerov:

```bash
make run-dev-build
```

2. Inicializácia databázy 
```bash
make seed-db
```
3. Zobrazenie logov (voliteľné):
```bash
make logs-dev
```


## Spustenie produkčného režimu

1. Vytvorenie a spustenie kontajnerov
```bash
make run-prod
```
2. Prístup k aplikácií na: https://example-domain.com (Táto doména sa nastavuje v Caddyfile)
3. Zastavenie produkčných kontrajnerov:
```bash
make stop-prod
```
5. (Voliteľné) Pre prípad, že potrebujete kompletne resetnúť aplikáciu:
```bash
make rm-volumes
```
Následne opakujte spustenie aplikácie znovu

## Po spustení je backend dostupný na:

Príkladový caddyfile setup:
```bash
{
    email example@mail.com
}

https://example-api.sk {
    handle_path /api/docs* {
        basicauth {
            admin $2a$14$drIJWG9SNhJDXkkdnR7t..qoK9YbccmQcgiZJ3GB.lRBw7yt871J2
        }
        rewrite * /api/docs{http.request.uri.path}
        reverse_proxy fastapi_server:8000
    }
    reverse_proxy fastapi_server:8000
}

```

- example-api.sk: Názov domény.
- handle_path: tu špecifikujeme presnú path kde sa môže napríklad nachádzať swagger
- reverse_proxy: Preposiela /api/* požiadavky na backend aplikáciu (napr. FastAPI).

##  Zmena EMAIL sekcie v env v budúcnosti

Ak potrebujete zmeniť hodnoty (napr. odosielateľa alebo SMTP server):

### Zmena SMTP v .env

- upraviť príslušné premenné v súbore .env
- aplikáciu reštartovať
```bash
make stop-prod / make stop-dev
make run-prod / make run-dev
```
- Databáza nebude ovplyvnená. Zmena e-mailových nastavení nijako neovplyvňuje existujúce dáta.

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