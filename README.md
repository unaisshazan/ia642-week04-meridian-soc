# IA 642 Lab 4.2 — Meridian Wazuh SOC

Student lab artifacts for standing up a single-node Wazuh SIEM (MERIDIAN-SOC01), onboarding MERIDIAN-DC01 and MERIDIAN-RED01, and deploying custom rules 100010 / 100011 / 100020.

## What is in this repo

- `submission/` — Canvas upload set: report PDF, Evidence #1–#8, rule XML, Tier 1 SOP
- `linux/soc01/` — files copied from the Ubuntu Wazuh manager (rules, sanitized manager config, agent list, service state)
- `linux/red01/` — sanitized Wazuh agent config from the Linux agent host

## What is not in this repo

Agent keys, `authd.pass`, dashboard admin passwords, and `wazuh-passwords.txt` are excluded on purpose.

## Hosts

| Host | Role |
|---|---|
| MERIDIAN-SOC01 | Wazuh 4.14 manager, indexer, dashboard (192.168.56.30) |
| MERIDIAN-DC01 | Windows agent |
| MERIDIAN-RED01 | Linux agent (Ubuntu) |

Dashboard (local lab only): `https://127.0.0.1:8443`
