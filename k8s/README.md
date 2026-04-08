# Kubernetes (e-infra / obecný cluster)

## Tok

1. **Push na `main`** (nebo vytvoření tagu) spustí [GitHub Actions](../.github/workflows/publish.yml) → image na **ghcr.io** s vestavěnými vahami HeSPI `sheet-component` (build arg `WEIGHTS_URL`).
2. V clusteru vytvořte **Secret** s přístupem k DB a S3 (viz `secret.yaml.example`).
3. Upravte **image** v `kustomization.yaml` (`newName` / `newTag` podle vašeho GHCR).
4. `kubectl apply -k k8s/`

## Příkazy

```bash
# Secret (jednou)
cp k8s/secret.yaml.example k8s/secret.yaml
# upravte hodnoty, pak:
kubectl apply -f k8s/secret.yaml

# Namespace + Deployment + Service (image z kustomization)
kubectl apply -k k8s/

# Stav
kubectl -n databots get pods,svc
kubectl -n databots logs -f deploy/herbarium-databots
```

## Co manifesty dělají

| Soubor | Účel |
|--------|------|
| `namespace.yaml` | Namespace `databots` |
| `deployment.yaml` | Běh `python src/main.py` — scheduler + worker pool + Flask na portu **5000** |
| `service.yaml` | `ClusterIP` na port 5000 (Ingress podle šablony clusteru) |
| `cronjob-coco-bbox.yaml` | Volitelně jen periodický běh `coco-bbox-detector` (přidejte do `kustomization.yaml`) |
| `secret.yaml.example` | Šablona proměnných `DB_*`, `S3_*` (stejné jako [`src/config/config.py`](../src/config/config.py)) |

## Privátní ghcr.io

Pokud je balíček image privátní, vytvořte pull secret a v `deployment.yaml` odkomentujte `imagePullSecrets`. Token GitHub s oprávněním `read:packages`.

## CronJob vs Deployment

- **Deployment** — trvale běžící služba (UI + plánovač dle `config.yaml`).
- **CronJob** — pouze dávkový běh `coco-bbox-detector` ve zvoleném intervalu; vhodné, když nechcete nechat běžet Flask 24/7.
