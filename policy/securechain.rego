package securechain

import rego.v1

# Par défaut, la pipeline est bloquée.
default allow := false

# Autoriser seulement si toutes les conditions sont respectées.
allow if {
    input.tests_passed == true
    input.secrets_found == 0
    input.high_vulnerabilities == 0
    input.critical_vulnerabilities == 0
    input.sbom_generated == true
    input.runs_as_root == false
}

# Raisons du blocage.
deny contains "Les tests ont échoué" if {
    input.tests_passed == false
}

deny contains "Un secret a été détecté" if {
    input.secrets_found > 0
}

deny contains "Des vulnérabilités HIGH ont été détectées" if {
    input.high_vulnerabilities > 0
}

deny contains "Des vulnérabilités CRITICAL ont été détectées" if {
    input.critical_vulnerabilities > 0
}

deny contains "Le SBOM est absent" if {
    input.sbom_generated == false
}

deny contains "Le conteneur fonctionne avec root" if {
    input.runs_as_root == true
}

# Statut final.
status := "ALLOW" if {
    allow
}

status := "BLOCK" if {
    not allow
}

# Décision complète retournée par OPA.
decision := {
    "allow": allow,
    "status": status,
    "reasons": deny
}