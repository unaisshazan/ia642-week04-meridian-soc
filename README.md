# Meridian Wazuh SOC (IA 642 Lab 4.2)

Eastern Michigan University — IA 642 Defensive Security, Week 04 Module 02.

**Authors:** Unais Ali, Hafiz Usama  
**Case:** Meridian Health Network  
**Report:** [`submission/Ali_Week04_Module02_Lab.pdf`](submission/Ali_Week04_Module02_Lab.pdf)  
**Repo:** https://github.com/unaisshazan/ia642-week04-meridian-soc

This repository is the lab project behind that report: a single-node Wazuh SIEM, two agents, custom detection rules, alert triage, and a tuned SSH rule with a Tier 1 playbook.

---

## What we are doing

We stand up a Security Operations Center (SOC) stack for a fictional clinic, **Meridian Health Network**, using **Wazuh 4.14** as the Security Information and Event Management (SIEM) system.

The work is detection engineering, not application development:

1. Collect endpoint telemetry (Windows + Linux).
2. Normalize and index it on one manager.
3. Write custom rules that turn raw events into analyst-facing alerts.
4. Triage eight overnight alerts as true positive (TP) or false positive (FP).
5. Tune the noisy SSH rule so a known retry-then-success pattern does not waste Tier 1 time, while a no-success burst still pages.

## Why we are doing it

Meridian needs a place where failed logins, Kerberos ticket abuse, and other credential-access behavior become visible in minutes, not after a helpdesk ticket. A small clinic cannot run a three-tier SIEM cluster. One Ubuntu host with manager, indexer, and dashboard is enough for about 100 agents and 90 days of alerts.

The academic goal is to practice the same loop a real SOC uses:

- deploy collection
- prove telemetry arrived (raw fields in Discover)
- write event-match and behavior-match rules
- measure Mean Time to Detect (MTTD)
- tune for alert fatigue without dropping the attack class

No production, campus, or employer host is used.

---

## Architecture

| Host | Role | Notes |
|---|---|---|
| **MERIDIAN-SOC01** | Wazuh manager, indexer, dashboard | Ubuntu, `192.168.56.30` |
| **MERIDIAN-DC01** | Windows agent | Domain-controller fallback: the Windows lab host |
| **MERIDIAN-RED01** | Linux agent | Ubuntu (WSL in this build) |

Local dashboard (lab VM only): `https://127.0.0.1:8443`

**Live-fire path:** Path 2 (SSH authentication failures on RED01). Path 1 (Kerberoasting / Windows 4769 RC4 TGS) is written into the rules so Part E triage still matches lecture, but it was not the live fire path because a working domain controller was not required.

Wazuh 4.14 journald collection classifies `Failed password` lines as built-in rule **5760** (not classic-syslog 5716). Custom rule 100020 is chained from 5760. The frequency logic is the same.

---

## What the report covers

| Section | Content |
|---|---|
| Fork note | Lab 4.1 reuse vs fallback hosts; Path 2 live fire |
| Part A | All-in-one SIEM deploy; Evidence #1 empty overview |
| Part B | Onboard DC01 and RED01; Evidence #2–#3 both Active |
| Part C | Raw SSH failure in Discover (source IP + username); Evidence #4 |
| Part D | Rules 100010 / 100011 / 100020; Evidence #5–#6 custom fire + supporting events |
| Part E | TP/FP table for 8 alerts; dispositions and next actions |
| CT #3 | MTTD: alert #1 = **4.67 min**, alert #6 = **3.00 min** |
| Challenge | Tuned 100020 (`same_field` dstuser) + Tier 1 SOP; Evidence #7–#8 |
| CT #1–#4 | Single-node risk, event vs behavior match, MTTD, alert-fatigue / stale tune |

### Custom rules

| ID | Type | Meaning |
|---|---|---|
| **100010** | Event match | One Kerberos TGS (4769) using RC4 (`0x17`) — T1558.003 |
| **100011** | Behavior match | Eight 100010 hits from the same source in 300 seconds |
| **100020** | Behavior match | Five SSH auth failures (parent 5760) from the same source in 120 seconds — T1110.001 |

Challenge tune adds `<same_field>dstuser</same_field>` so a same-IP spray across many usernames is not treated as one account retry. The VPN/job false positive is still one username, so XML alone cannot suppress it. The **Tier 1 SOP** closes a 100020 if the same source and account get a successful SSH (rule 5715) within 120 seconds.

### Part E triage (summary)

| # | TP/FP | ATT&CK | Disposition |
|---|---|---|---|
| 1 | TP | T1558.003 | Escalate (roast burst) |
| 2 | TP | T1110.003 | Escalate (root brute, then success) |
| 3 | TP | T1110.003 | Escalate (password spray) |
| 4 | FP | none | Close / tune 100010 (legacy print SPN) |
| 5 | FP | none | Close / tune 100020 (job retry then success) |
| 6 | TP | T1558.003 | Escalate urgent (admin host, many SPNs) |
| 7 | FP | none | Close / tune 5720 (no SSH listener) |
| 8 | FP | none | Close (spaced ETL tickets, no 100011) |

---

## What we achieved

- Wazuh 4.14 all-in-one running on MERIDIAN-SOC01.
- Two agents **Active**: MERIDIAN-DC01 (Windows) and MERIDIAN-RED01 (Linux).
- Raw SSH failure telemetry in Discover (Evidence #4).
- Custom rule **100020** fired at level 10 with MITRE T1110.001 (Evidence #5).
- Supporting 5760 events from the same source and username (Evidence #6).
- Tuned rule plus SOP: retry-then-success is a close, not an escalate (Evidence #7).
- The original no-success burst still raises 100020 (Evidence #8).
- Written triage, MTTD arithmetic, and all four critical-thinking answers in the PDF.

Screenshots live in `submission/Evidence1_*.png` … `Evidence8_*.png`.

---

## How to use this project

This is **configuration and detection content**, not a mobile/web app. You need your own lab Wazuh manager. Do not point these files at a production or campus SIEM.

### 1. Read the report

Open [`submission/Ali_Week04_Module02_Lab.pdf`](submission/Ali_Week04_Module02_Lab.pdf).

### 2. Deploy the final rules (Challenge-tuned)

On the Wazuh manager, as root:

```bash
# backup
cp -a /var/ossec/etc/rules/local_rules.xml /var/ossec/etc/rules/local_rules.xml.bak

# copy this repo file
cp submission/local_rules.xml /var/ossec/etc/rules/local_rules.xml
chown root:wazuh /var/ossec/etc/rules/local_rules.xml
chmod 660 /var/ossec/etc/rules/local_rules.xml

# syntax check, then restart
/var/ossec/bin/wazuh-analysisd -t
systemctl restart wazuh-manager
systemctl is-active wazuh-manager
```

- `submission/local_rules.xml` — **final** tuned 100020 (`same_source_ip` + `same_field` dstuser).
- `submission/local_rules_partD.xml` — Part D version (same source IP only), if you want to replay the pre-tune fire.
- `linux/soc01/local_rules.xml` — copy taken from the live manager after the tune.

### 3. Apply the playbook

Read [`submission/Tier1_SOP_100020.txt`](submission/Tier1_SOP_100020.txt).

On every 100020 alert, search the next 120 seconds for rule **5715** (SSH success) for the same source IP and username. Close if that success is a known staff or service account. Escalate if there is no success, or the account is unused / root / unknown.

### 4. Reference configs (do not overwrite blindly)

| File | Use |
|---|---|
| `linux/soc01/ossec.conf` | Sanitized manager config from this lab |
| `linux/red01/ossec.conf` | Sanitized Linux agent config (`WAZUH_MANAGER=192.168.56.30`, name `MERIDIAN-RED01`) |
| `linux/soc01/opensearch_dashboards.yml` | Dashboard timeout / session settings used in the lab |
| `linux/soc01/agents.txt` | Agent list at export time |

Agent keys, `authd.pass`, and dashboard passwords are **not** in this repo. Use the password file created by the official Wazuh installer on your own VM.

### 5. Official installer (high level)

Wazuh documents the all-in-one install. On a dedicated Ubuntu lab VM (not this GitHub checkout):

```text
https://documentation.wazuh.com/current/installation-guide/index.html
```

Then install agents with `WAZUH_MANAGER=<manager-ip>` and register them. This repository does not include the installer or any attack tooling.

### 6. Discover searches used in the lab (DQL)

```
rule.id : 5760
rule.id : 100020
rule.id : 5715 or rule.id : 5760
```

Use spaces around `:` when the search language is DQL.

---

## Limitations

- **Single node.** Manager, indexer, and dashboard share one VM. If that host dies, collection and search history both stop (Critical thinking #1).
- **No live Kerberoasting path.** 100010 / 100011 are deployed for triage and lecture alignment. They were not proven with a live 4769 / 0x17 fire in this build.
- **Journald vs classic syslog.** Parent SID is 5760 here. A classic-syslog lab that only fires 5716 needs `<if_matched_sid>5716</if_matched_sid>` or a group match.
- **SOP is human, not XML.** Wazuh cannot cleanly express “not followed by success.” VPN retry suppression depends on analysts following the playbook.
- **Same-account tune is incomplete alone.** `dstuser` still matches the VPN false-positive class (one user, many retries). Raising frequency would miss the five-failure burst.
- **Lab network only.** Host-only / NAT addresses (`192.168.56.30`, `10.0.2.15`) are not reachable from the internet. This is not a hosted Wazuh Cloud or Firebase app.
- **Home Windows agent.** DC01 is a Windows 11 fallback, not a real clinic domain controller. CIS/SCA scores on that host are not evidence for this lab.
- **Student identifiers.** The PDF includes names and EIDs. Keep that in mind if the repository stays public.

---

## Future work

- Prove Path 1 when a domain controller is available: one 4769 with `TicketEncryptionType` 0x17, then a burst that fires 100011.
- Keep a replay set (one retry-then-success fixture, one no-success burst) and re-run it after any VPN or jump-host change (Critical thinking #4).
- Watch 100020 volume for two weeks before calling the tune stable.
- Split indexer and dashboard off the manager if Meridian grows past a single-node profile.
- Add a detection for password spray (many usernames, one source) as its own rule, separate from 100020.
- Store rules in git and promote them with a checked `wazuh-analysisd -t` step so a bad XML cannot take the manager down.

---

## Repository layout

```text
submission/
  Ali_Week04_Module02_Lab.pdf    Full lab report (Evidence #1–#8, Part E, MTTD, CT #1–#4)
  Evidence1_…Evidence8_*.png     Student dashboard captures
  local_rules.xml                Final tuned rules
  local_rules_partD.xml          Pre-tune 100020
  Tier1_SOP_100020.txt           Close-if-success playbook
linux/soc01/                     Live manager export (sanitized)
linux/red01/                     Live Linux agent export (sanitized)
```

**Never committed:** `client.keys`, `authd.pass`, `wazuh-passwords.txt`, dashboard admin passwords.

---

## License / course use

Course lab artifacts for IA 642. Not a production SIEM. Do not reuse the rules against systems you do not own or administer.
