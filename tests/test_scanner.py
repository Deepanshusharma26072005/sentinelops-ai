from scanner.misconfig_scanner import check_nsgs, check_storage, scan


def rule(name, source, ports, access="Allow"):
    return {
        "name": name,
        "access": access,
        "direction": "Inbound",
        "sourceAddressPrefix": source,
        "destinationPortRange": ports,
    }


SAFE_NSG = {
    "name": "nsg-safe",
    "securityRules": [rule("ssh-from-my-ip", "203.0.113.5/32", "22")],
}

RISKY_NSG = {
    "name": "nsg-risky",
    "securityRules": [
        rule("ssh-from-anywhere", "*", "22"),
        rule("everything-open", "0.0.0.0/0", "*"),
        rule("app-open", "Internet", "8000"),
        rule("blocked-ssh", "*", "22", access="Deny"),
    ],
}

SAFE_STORAGE = {
    "name": "stsafe",
    "allowBlobPublicAccess": False,
    "enableHttpsTrafficOnly": True,
    "minimumTlsVersion": "TLS1_2",
    "networkRuleSet": {"defaultAction": "Deny"},
}

RISKY_STORAGE = {
    "name": "strisky",
    "allowBlobPublicAccess": True,
    "enableHttpsTrafficOnly": False,
    "minimumTlsVersion": "TLS1_0",
    "networkRuleSet": {"defaultAction": "Allow"},
}


def test_safe_nsg_has_no_findings():
    assert check_nsgs([SAFE_NSG]) == []


def test_risky_nsg_findings():
    severities = sorted(f["severity"] for f in check_nsgs([RISKY_NSG]))
    assert severities == ["CRITICAL", "HIGH", "MEDIUM"]


def test_deny_rules_are_ignored():
    assert check_nsgs([{"name": "n", "securityRules": [rule("d", "*", "22", "Deny")]}]) == []


def test_safe_storage_has_no_findings():
    assert check_storage([SAFE_STORAGE]) == []


def test_risky_storage_findings():
    severities = sorted(f["severity"] for f in check_storage([RISKY_STORAGE]))
    assert severities == ["HIGH", "HIGH", "MEDIUM", "MEDIUM"]


def test_scan_sorts_worst_first():
    findings = scan([RISKY_NSG], [RISKY_STORAGE])
    assert findings[0]["severity"] == "CRITICAL"
    assert len(findings) == 7
