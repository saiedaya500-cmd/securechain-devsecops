package securechain_test

import rego.v1
import data.securechain

test_allow_secure_project if {
    securechain.allow with input as {
        "tests_passed": true,
        "secrets_found": 0,
        "high_vulnerabilities": 0,
        "critical_vulnerabilities": 0,
        "sbom_generated": true,
        "runs_as_root": false
    }
}

test_block_project_with_secret if {
    not securechain.allow with input as {
        "tests_passed": true,
        "secrets_found": 1,
        "high_vulnerabilities": 0,
        "critical_vulnerabilities": 0,
        "sbom_generated": true,
        "runs_as_root": false
    }
}

test_block_project_with_high_vulnerability if {
    not securechain.allow with input as {
        "tests_passed": true,
        "secrets_found": 0,
        "high_vulnerabilities": 1,
        "critical_vulnerabilities": 0,
        "sbom_generated": true,
        "runs_as_root": false
    }
}

test_block_project_without_sbom if {
    not securechain.allow with input as {
        "tests_passed": true,
        "secrets_found": 0,
        "high_vulnerabilities": 0,
        "critical_vulnerabilities": 0,
        "sbom_generated": false,
        "runs_as_root": false
    }
}

test_block_container_running_as_root if {
    not securechain.allow with input as {
        "tests_passed": true,
        "secrets_found": 0,
        "high_vulnerabilities": 0,
        "critical_vulnerabilities": 0,
        "sbom_generated": true,
        "runs_as_root": true
    }
}

test_block_when_tests_fail if {
    not securechain.allow with input as {
        "tests_passed": false,
        "secrets_found": 0,
        "high_vulnerabilities": 0,
        "critical_vulnerabilities": 0,
        "sbom_generated": true,
        "runs_as_root": false
    }
}