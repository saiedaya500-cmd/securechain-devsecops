import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from threading import Lock

import httpx


GITHUB_OWNER = "saiedaya500-cmd"
GITHUB_REPOSITORY = "securechain-devsecops"
GITHUB_BRANCH = "main"

CACHE_DURATION_SECONDS = 120

WORKFLOWS = [
    {
        "name": "Application Tests",
        "tool": "Pytest / CI",
        "file": "ci.yml",
        "description": (
            "Tests fonctionnels et construction "
            "de l'image Docker."
        ),
    },
    {
        "name": "Static Code Analysis",
        "tool": "Semgrep",
        "file": "semgrep.yml",
        "description": (
            "Analyse statique du code et détection "
            "des erreurs de sécurité."
        ),
    },
    {
        "name": "Secret Detection",
        "tool": "Gitleaks",
        "file": "gitleaks.yml",
        "description": (
            "Recherche de secrets exposés "
            "dans le dépôt Git."
        ),
    },
    {
        "name": "Vulnerability Scan",
        "tool": "Trivy",
        "file": "trivy.yml",
        "description": (
            "Analyse des dépendances "
            "et de l'image Docker."
        ),
    },
    {
        "name": "Software Bill of Materials",
        "tool": "Syft SBOM",
        "file": "sbom.yml",
        "description": (
            "Génération de l'inventaire "
            "CycloneDX des composants."
        ),
    },
    {
        "name": "Security Policy Decision",
        "tool": "OPA",
        "file": "opa.yml",
        "description": (
            "Décision finale selon les résultats "
            "des contrôles de sécurité."
        ),
    },
]

ALLOWED_WORKFLOW_FILES = {
    workflow["file"]
    for workflow in WORKFLOWS
}

_cache_lock = Lock()

_cache = {
    "expires_at": 0.0,
    "data": None,
}


def normalize_workflow_status(
    status: str | None,
    conclusion: str | None,
) -> str:
    if status != "completed":
        return "RUNNING"

    if conclusion == "success":
        return "PASS"

    if conclusion in {
        "failure",
        "cancelled",
        "timed_out",
        "action_required",
        "stale",
    }:
        return "FAIL"

    return "UNKNOWN"


def empty_workflow_result(
    workflow: dict,
    message: str,
) -> dict:
    return {
        **workflow,
        "status": "UNKNOWN",
        "conclusion": None,
        "url": None,
        "updated_at": None,
        "head_sha": None,
        "commit_message": None,
        "message": message,
    }


def fetch_workflow_status(workflow: dict) -> dict:
    workflow_file = workflow["file"]

    if workflow_file not in ALLOWED_WORKFLOW_FILES:
        return empty_workflow_result(
            workflow,
            "Workflow non autorisé.",
        )

    url = (
        f"https://api.github.com/repos/{GITHUB_OWNER}/"
        f"{GITHUB_REPOSITORY}/actions/workflows/"
        f"{workflow_file}/runs"
        f"?branch={GITHUB_BRANCH}&per_page=1"
    )

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "SecureChain-Dashboard",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    github_token = os.getenv("GITHUB_TOKEN")

    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    try:
        with httpx.Client(
            headers=headers,
            timeout=8.0,
            follow_redirects=False,
        ) as client:
            response = client.get(url)
            response.raise_for_status()
            payload = response.json()

        workflow_runs = payload.get("workflow_runs", [])

        if not workflow_runs:
            return empty_workflow_result(
                workflow,
                "Aucune exécution trouvée.",
            )

        latest_run = workflow_runs[0]
        head_commit = latest_run.get("head_commit") or {}

        return {
            **workflow,
            "status": normalize_workflow_status(
                latest_run.get("status"),
                latest_run.get("conclusion"),
            ),
            "conclusion": latest_run.get("conclusion"),
            "url": latest_run.get("html_url"),
            "updated_at": latest_run.get("updated_at"),
            "head_sha": latest_run.get("head_sha"),
            "commit_message": head_commit.get("message"),
            "message": None,
        }

    except (httpx.HTTPError, ValueError) as error:
        return empty_workflow_result(
            workflow,
            (
                "Résultat indisponible : "
                f"{type(error).__name__}"
            ),
        )


def fetch_all_workflows() -> list[dict]:
    results: list[dict | None] = [None] * len(WORKFLOWS)

    with ThreadPoolExecutor(
        max_workers=len(WORKFLOWS)
    ) as executor:
        futures = {
            executor.submit(
                fetch_workflow_status,
                workflow,
            ): index
            for index, workflow in enumerate(WORKFLOWS)
        }

        for future in as_completed(futures):
            index = futures[future]
            results[index] = future.result()

    return [
        result
        for result in results
        if result is not None
    ]


def get_latest_commit(checks: list[dict]) -> dict:
    checks_with_commit = [
        check
        for check in checks
        if check.get("head_sha")
    ]

    if not checks_with_commit:
        return {
            "sha": None,
            "short_sha": None,
            "message": None,
            "url": None,
        }

    latest_check = max(
        checks_with_commit,
        key=lambda check: check.get("updated_at") or "",
    )

    commit_sha = latest_check["head_sha"]

    return {
        "sha": commit_sha,
        "short_sha": commit_sha[:7],
        "message": latest_check.get("commit_message"),
        "url": (
            f"https://github.com/{GITHUB_OWNER}/"
            f"{GITHUB_REPOSITORY}/commit/{commit_sha}"
        ),
    }


def get_security_dashboard_data(
    force_refresh: bool = False,
) -> dict:
    current_time = time.monotonic()

    with _cache_lock:
        cached_data = _cache["data"]
        cache_is_valid = (
            current_time < _cache["expires_at"]
        )

        if (
            not force_refresh
            and cached_data is not None
            and cache_is_valid
        ):
            return cached_data

    checks = fetch_all_workflows()

    passed = sum(
        check["status"] == "PASS"
        for check in checks
    )

    failed = sum(
        check["status"] == "FAIL"
        for check in checks
    )

    running = sum(
        check["status"] == "RUNNING"
        for check in checks
    )

    unknown = sum(
        check["status"] == "UNKNOWN"
        for check in checks
    )

    pending = running + unknown
    total_checks = len(checks)

    if failed > 0:
        decision = "BLOCK"
    elif pending > 0:
        decision = "UNKNOWN"
    elif total_checks > 0 and passed == total_checks:
        decision = "ALLOW"
    else:
        decision = "UNKNOWN"

    latest_commit = get_latest_commit(checks)

    data = {
        "checks": checks,
        "decision": decision,
        "passed": passed,
        "failed": failed,
        "pending": pending,
        "repository": GITHUB_REPOSITORY,
        "branch": GITHUB_BRANCH,
        "latest_commit": latest_commit,
        "generated_at": datetime.now(
            timezone.utc
        ).strftime("%Y-%m-%d %H:%M UTC"),
    }

    with _cache_lock:
        _cache["data"] = data
        _cache["expires_at"] = (
            time.monotonic()
            + CACHE_DURATION_SECONDS
        )

    return data