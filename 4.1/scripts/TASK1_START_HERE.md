# Lab 4.1 — Task tracker (do one task, then stop and confirm)

You already have VirtualBox + `MERIDIAN-RED01` (Kali) + `MERIDIAN-SOC01` (from Module 02).
Lab 4.1 needs a **new** Windows Server DC: `MERIDIAN-DC01`.

Internal network name already exists: `meridian-lab-net`.

---

## TASK 1 (now) — Get Windows Server 2022 ISO + create DC01 VM

### 1A. Download ISO (required — not on this PC yet)

1. Open: https://www.microsoft.com/en-us/evalcenter/download-windows-server-2022  
2. Download **Windows Server 2022** evaluation ISO (180 days, Desktop Experience).  
3. Save it somewhere easy, e.g. `C:\Users\unais\Downloads\WindowsServer2022.iso`  
4. Reply here with the full path when the download finishes.

### 1B. After ISO is ready — I will create the VM for you with:

| Setting | Value |
|--------|--------|
| Name | MERIDIAN-DC01 |
| Type | Windows Server 2022 (64-bit) |
| RAM | 5120 MB |
| Disk | 80 GB dynamic |
| NIC1 | NAT (setup only) |
| NIC2 | Internal Network `meridian-lab-net` |

### 1C. Reconfigure RED01 for this lab

| Setting | Change to |
|--------|-----------|
| NIC2 | Internal Network `meridian-lab-net` (not Host-Only) |
| RAM | bump to 3072 MB if host has free memory |

Do **not** start Parts B–E until both VMs ping on `10.77.0.0/24`.

---

## After Task 1 (preview)

| Task | What |
|------|------|
| 2 | Install Server + static IP 10.77.0.10 + rename + promote AD |
| 3 | Part B: svc-billingsql SPN + j.reyes + Evidence #1–#2 |
| 4 | Part C: Kerberoast + hashcat + Evidence #3–#4 |
| 5 | Part D: gMSA + Evidence #5–#6 |
| 6 | Part E: Keycloak PKCE + Evidence #7–#8 |
| 7 | AES-only challenge + Evidence #9 + finish PDF |

**Your move right now:** start the Server 2022 ISO download and paste the path when done.
