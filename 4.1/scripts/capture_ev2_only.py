"""Clean Evidence #2 capture as j.reyes."""
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

VB = r"C:\Program Files\Oracle\VirtualBox\VBoxManage.exe"
LAB = Path(r"c:\Users\unais\OneDrive - Eastern Michigan University\Documents\Fall 2026\IA\week 4\4.1")
EV = LAB / "evidence"
FIG = EV / "figures"

cmd = (
    "whoami; Write-Host ''; "
    "klist purge; Write-Host ''; "
    "klist get MSSQLSvc/billing.meridian.local:1433; Write-Host ''; "
    "klist"
)
args = [
    VB, "guestcontrol", "MERIDIAN-DC01", "run",
    "--username", "j.reyes",
    "--password", "ClinicUser2026!",
    "--timeout", "120000",
    "--wait-stdout", "--wait-stderr",
    "--exe", r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
    "--", "-NoProfile", "-Command", cmd,
]
p = subprocess.run(args, capture_output=True, timeout=150)
# decode as utf-8 / utf-16 / cp1252
raw = p.stdout or b""
for enc in ("utf-8", "utf-16-le", "cp1252", "latin-1"):
    try:
        out = raw.decode(enc)
        if "j.reyes" in out or "MSSQLSvc" in out:
            break
    except Exception:
        out = raw.decode("latin-1", errors="replace")

err = (p.stderr or b"").decode("utf-8", errors="replace")
# keep only useful lines
lines = []
for ln in (out + "\n" + err).splitlines():
    if any(x in ln for x in ("VBoxManage", "NativeCommandError", "CategoryInfo", "FullyQualified", "+ &", "+ ~~~")):
        continue
    lines.append(ln.rstrip())
body = "\n".join(lines).strip()
text = (
    "Evidence #2 – klist as j.reyes @ MERIDIAN-DC01\n"
    "Commands: klist purge; klist get MSSQLSvc/billing.meridian.local:1433; klist\n\n"
    + body
    + "\n"
)
(EV / "ev2_klist.txt").write_text(text, encoding="utf-8")
print(text)
print("--- bytes", len(text.encode("utf-8")))

img = Image.new("RGB", (1200, 860), (18, 22, 28))
d = ImageDraw.Draw(img)
try:
    font = ImageFont.truetype("consola.ttf", 15)
    fb = ImageFont.truetype("consola.ttf", 17)
except Exception:
    font = fb = ImageFont.load_default()
d.text((20, 14), "Evidence #2 – klist as j.reyes (MSSQLSvc/billing TGS)", fill=(90, 180, 255), font=fb)
y = 46
for ln in text.splitlines():
    if y > 830:
        break
    d.text((20, y), ln[:145], fill=(220, 220, 220), font=font)
    y += 18
outp = FIG / "fig_ev2.png"
img.save(outp)
print("wrote", outp, outp.stat().st_size)
print("EV2_OK" if "MSSQLSvc" in text and "j.reyes" in text else "EV2_WEAK")
