# Spouštění databotů

Stručný návod k lokálnímu běhu. Aplikace očekává běžící PostgreSQL (schéma `databots`) a pro boty pracující s obrázky i S3/MinIO podle [`src/config.yaml`](../src/config.yaml).

## Příprava

```bash
cd /cesta/k/repozitari
poetry install
```

Verzi Pythonu sjednoťte s projektem (viz `pyproject.toml`), např.:

```bash
poetry env use python3.13
```

Údaje o DB a S3 upravte v `src/config.yaml`, případně přepište proměnnými prostředí ve tvaru `DB_*` a `S3_*` (viz [`src/config/config.py`](../src/config/config.py)).

## Jeden bot (jednorázový běh)

Spusťte vstupní skript s **názvem bota** jako prvním argumentem. Bot se zaregistruje v DB a zpracuje dávku záznamů podle své logiky.

```bash
poetry run python src/main.py <název_bota>
```

Stejně funguje i `src/test.py` (historicky duplicitní vstup).

**Registrované názvy:**

| Název | Popis |
|--------|--------|
| `database_connection_tester` | Test připojení k databázi |
| `no-ref-image-metrics` | Metriky kvality obrázku (BRISQUE apod.) |
| `cetaf_metadata` | Stahování metadat z CETAF SID |
| `coco-bbox-detector` | YOLO detekce bboxů → výsledky do DB + volitelně sloučený COCO JSON |

Příklady:

```bash
poetry run python src/main.py database_connection_tester
poetry run python src/main.py coco-bbox-detector
```

## Všechny boty (scheduler + web UI)

Bez argumentu se spustí fronta úloh, plánovač podle cron výrazů v `config.yaml` (sekce `bots:`) a Flask rozhraní na portu z `application.port` (výchozí 5000).

```bash
poetry run python src/main.py
```

Ukončení: `Ctrl+C`.

## Bot `coco-bbox-detector`

- Konfigurace v `config.yaml` pod klíčem `coco-bbox-detector`: `weights_path`, `conf_threshold`, `device`, `output_coco_path` (prázdné = žádný soubor na disku).
- Volitelně lze přepsat proměnnými: `YOLO_WEIGHTS_PATH`, `YOLO_CONF`, `YOLO_DEVICE`, `OUTPUT_COCO_PATH`.

### Váhy YOLO přímo v Docker image

Chcete-li mít soubor `.pt` **už zabudovaný v image** (typicky pro Kubernetes bez mountu modelu):

1. Při **buildu** předejte `WEIGHTS_URL` — přímý **HTTP(S)** odkaz na soubor vah. [`Dockerfile`](../Dockerfile) uloží výsledek jako `/app/weights/model.pt`. Končí-li URL na **`.gz`**, image si soubor nejdřív stáhne a **rozbalí** (stejně jako [HeSPI](https://github.com/rbturnbull/hespi) u modelů z GitHub releases).
2. V [`config.yaml`](../src/config.yaml) nechte `coco-bbox-detector.weights_path: "/app/weights/model.pt"` (výchozí v repozitáři), případně stejnou cestu nastavte env `YOLO_WEIGHTS_PATH` v manifestu.

Pro **sheet-component model** z projektu [hespi](https://github.com/rbturnbull/hespi) (výchozí YOLO pro části archu):

```bash
docker build \
  --build-arg WEIGHTS_URL="https://github.com/rbturnbull/hespi/releases/download/v0.4.0/sheet-component.pt.gz" \
  -t databots:local .
```

Jiný příklad — už rozbalený `.pt` z vlastního serveru:

```bash
docker build \
  --build-arg WEIGHTS_URL="https://example.com/muj-model.pt" \
  -t databots:local .
```

V CI (GitHub Actions apod.) často předáváte URL z tajného úložiště nebo z release artefaktu. Bez `WEIGHTS_URL` se krok stahování přeskočí a soubor v image nebude — pak musíte váhy dodat jinak (mount, init container).

## Docker

```bash
docker build -t databots .
docker run --rm --network host databots database_connection_tester
docker run --rm --network host databots coco-bbox-detector
```

U běhu v kontejneru nastavte DB/S3 přes env nebo mountovaný `config.yaml` podle vašeho nasazení.

## GitHub Actions → ghcr.io → Kubernetes

Po pushi na **`main`** se z [.github/workflows/publish.yml](../.github/workflows/publish.yml) sestaví image s HeSPI `sheet-component` a nahraje se na **ghcr.io**. Manifesty pro cluster jsou v [`k8s/`](../k8s/) (návod v [`k8s/README.md`](../k8s/README.md)): Secret s `DB_*` / `S3_*`, úprava image v `kustomization.yaml`, pak `kubectl apply -k k8s/`.
