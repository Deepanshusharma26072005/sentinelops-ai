"""Simple cloud misconfiguration scanner for Azure resources.

Reads JSON produced by the Azure CLI and reports risky settings.
"""

import argparse
import json
import sys

SENSITIVE_PORTS = {
    22: "SSH",
    3389: "RDP",
    1433: "SQL Server",
    3306: "MySQL",
    5432: "PostgreSQL",
}
OPEN_SOURCES = {"*", "0.0.0.0/0", "internet", "any"}
SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}


def finding(severity, resource, message):
    return {"severity": severity, "resource": resource, "message": message}


def covers_port(spec, port):
    spec = str(spec).strip()
    if spec == "*":
        return True
    try:
        if "-" in spec:
            low, high = spec.split("-", 1)
            return int(low) <= port <= int(high)
        return int(spec) == port
    except ValueError:
        return False


def is_open_source(rule):
    prefixes = [rule.get("sourceAddressPrefix")]
    prefixes += list(rule.get("sourceAddressPrefixes") or [])
    return any(p and p.lower() in OPEN_SOURCES for p in prefixes)


def rule_ports(rule):
    ports = [rule.get("destinationPortRange")]
    ports += list(rule.get("destinationPortRanges") or [])
    return [p for p in ports if p]


def check_nsgs(nsgs):
    findings = []
    for nsg in nsgs:
        resource = f"NSG {nsg.get('name')}"
        for rule in nsg.get("securityRules") or []:
            if rule.get("access") != "Allow":
                continue
            if rule.get("direction") != "Inbound":
                continue
            if not is_open_source(rule):
                continue
            name = rule.get("name")
            ports = rule_ports(rule)
            if "*" in ports:
                findings.append(
                    finding(
                        "CRITICAL",
                        resource,
                        f"rule '{name}' allows ALL ports from the internet",
                    )
                )
                continue
            exposed = [
                (port, service)
                for port, service in SENSITIVE_PORTS.items()
                if any(covers_port(spec, port) for spec in ports)
            ]
            for port, service in exposed:
                findings.append(
                    finding(
                        "HIGH",
                        resource,
                        f"rule '{name}' exposes {service} (port {port}) "
                        "to the internet",
                    )
                )
            if ports and not exposed:
                findings.append(
                    finding(
                        "MEDIUM",
                        resource,
                        f"rule '{name}' opens port(s) {', '.join(ports)} "
                        "to the internet",
                    )
                )
    return findings


def check_storage(accounts):
    findings = []
    for account in accounts:
        resource = f"Storage account {account.get('name')}"
        if account.get("allowBlobPublicAccess") is True:
            findings.append(
                finding("HIGH", resource, "public blob access is allowed")
            )
        if account.get("enableHttpsTrafficOnly") is False:
            findings.append(
                finding("HIGH", resource, "HTTPS-only traffic is not enforced")
            )
        tls = account.get("minimumTlsVersion")
        if tls in ("TLS1_0", "TLS1_1"):
            findings.append(
                finding("MEDIUM", resource, f"old TLS version allowed ({tls})")
            )
        rules = account.get("networkRuleSet") or {}
        if rules.get("defaultAction") == "Allow":
            findings.append(
                finding("MEDIUM", resource, "storage firewall allows all networks")
            )
    return findings


def scan(nsgs, storage_accounts):
    findings = check_nsgs(nsgs) + check_storage(storage_accounts)
    return sorted(findings, key=lambda item: SEVERITY_ORDER[item["severity"]])


def load(path):
    if not path:
        return []
    with open(path) as handle:
        return json.load(handle)


def main():
    parser = argparse.ArgumentParser(description="Scan Azure settings for risks")
    parser.add_argument("--nsg", help="JSON from: az network nsg list -o json")
    parser.add_argument(
        "--storage", help="JSON from: az storage account list -o json"
    )
    args = parser.parse_args()

    findings = scan(load(args.nsg), load(args.storage))
    if not findings:
        print("No misconfigurations found.")
        return 0
    for item in findings:
        print(f"[{item['severity']}] {item['resource']}: {item['message']}")
    print(f"\n{len(findings)} finding(s).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
