# SecureChain — Phase 1: SecureShop

SecureShop est une petite application web FastAPI utilisée comme cas d'étude pour construire progressivement un pipeline DevSecOps de sécurité de la chaîne logicielle.

## Fonctionnalités actuelles

- catalogue de produits ;
- ajout, modification, suppression et recherche ;
- persistance SQLite ;
- validation des entrées ;
- endpoint `/health` ;
- documentation API `/docs` ;
- tests Pytest ;
- image Docker non-root avec health check ;
- workflow CI GitHub Actions.

## Lancer localement

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Ouvrir `http://127.0.0.1:8000`.

## Lancer avec Docker

```bash
docker build -t secureshop:local .
docker run --rm -p 8000:8000 secureshop:local
```

## Tests

```bash
pytest -q
```

## Prochaines phases

1. SAST avec Semgrep.
2. Détection des secrets avec Gitleaks.
3. Scan des dépendances et de l'image avec Trivy.
4. SBOM avec Syft.
5. Security Gates, signature Cosign et surveillance Falco.
