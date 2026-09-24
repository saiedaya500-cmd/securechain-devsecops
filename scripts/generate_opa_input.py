import json
import os
from pathlib import Path


def get_bool(name: str) -> bool:
    return os.getenv(name, "false").lower() == "true"


def get_int(name: str) -> int:
    return int(os.getenv(name, "0"))


opa_input = {
    "tests_passed": get_bool("TESTS_PASSED"),
    "secrets_found": get_int("SECRETS_FOUND"),
    "high_vulnerabilities": get_int("HIGH_VULNERABILITIES"),
    "critical_vulnerabilities": get_int("CRITICAL_VULNERABILITIES"),
    "sbom_generated": get_bool("SBOM_GENERATED"),
    "runs_as_root": get_bool("RUNS_AS_ROOT"),
}

output_file = Path("policy/input-ci.json")
output_file.write_text(
    json.dumps(opa_input, indent=2),
    encoding="utf-8",
)

print("Entrée OPA générée :")
print(json.dumps(opa_input, indent=2))