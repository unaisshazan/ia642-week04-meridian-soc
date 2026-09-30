# Lab 4.1 command cheat sheet (Meridian)

Isolated net: `meridian-lab-net` · DC `10.77.0.10` · RED `10.77.0.20` · Disconnect NAT before Parts B–E.

## Evidence order

| # | Where | Command / what to show |
|---|--------|-------------------------|
| 1 | DC01 | `setspn -L svc-billingsql` |
| 2 | DC01 | `klist get MSSQLSvc/...` then `klist` (note encryption type) |
| 3 | RED01 | `GetUserSPNs.py ... -request` + `cat meridian_tgs.hashes` |
| 4 | RED01 | `hashcat -m 13100 ... --show` → Cracked / Summer2019! |
| 5 | DC01 | `Test-ADServiceAccount` True + managed password interval |
| 6 | RED01 | hashcat against gMSA hashes → no human crack |
| 7 | RED01 | `token_response.json` |
| 8 | RED01 | Python JWT header + payload decode |
| 9 | DC01 | After AES `0x18`: fresh `klist` shows AES not RC4 |

## Critical thinking (already written in report)

1. KDC issues TGS to any authenticated user; SPN request is not privileged.
2. T1558.003; lockout useless offline; detect with 4769.
3. gMSA ≠ least privilege / who retrieves password / Golden-Silver tickets.
4. Decode ≠ signature verify; forged `admin` role example.
5. AES alone ≠ enough if password still Summer2019!; gMSA makes strength irrelevant.

## Submit

`Ali_Week04_Module01_Lab.pdf` with all 9 evidence figures + CT #1–#5.

Module 02 (Wazuh) is already done: `IA/week 4/Ali_Week04_Module02_Lab.pdf`.
