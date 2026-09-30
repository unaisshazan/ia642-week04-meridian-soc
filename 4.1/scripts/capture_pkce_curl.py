"""PKCE auth-code via curl cookie jar (fixes Keycloak 'Cookie not found')."""
import json
import os
import re
import time

import paramiko
from PIL import Image, ImageDraw, ImageFont

PW = "REDACTED_SET_VIA_ENV"
LAB = r"c:\Users\unais\OneDrive - Eastern Michigan University\Documents\Fall 2026\IA\week 4\4.1"
EV = os.path.join(LAB, "evidence")
FIG = os.path.join(EV, "figures")

REMOTE_SH = r'''
set -euo pipefail
BASE=http://127.0.0.1:8080
export REDIRECT='http://127.0.0.1:8081/callback'
CLIENT=meridian-billing-app
USER=j.reyes
PASS='ClinicalUser2026!'
CJ=/tmp/kc_cj.txt
rm -f "$CJ" /tmp/kc_auth.html /tmp/kc_post.hdr /tmp/kc_post.body

# PKCE
VERIFIER=$(openssl rand -base64 96 | tr -d '=+/' | cut -c1-64)
CHALLENGE=$(printf '%s' "$VERIFIER" | openssl dgst -sha256 -binary | openssl base64 -A | tr '+/' '-_' | tr -d '=')
echo "VERIFIER_LEN=${#VERIFIER}"
echo "CHALLENGE=$CHALLENGE"

REDIR_ENC=$(python3 -c "import urllib.parse,os; print(urllib.parse.quote(os.environ['REDIRECT'], safe=''))")
AUTH_URL="$BASE/realms/meridian/protocol/openid-connect/auth?client_id=$CLIENT&response_type=code&scope=openid&redirect_uri=${REDIR_ENC}&code_challenge=$CHALLENGE&code_challenge_method=S256&state=lab41pkce"

# 1) GET login page with cookies
curl -sS -c "$CJ" -b "$CJ" -D /tmp/kc_auth.hdr -o /tmp/kc_auth.html "$AUTH_URL"
echo "COOKIES_AFTER_GET:"
cat "$CJ" || true
echo "---"
# show set-cookie lines
grep -i 'set-cookie' /tmp/kc_auth.hdr || true

# 2) Parse form action (unescape &amp;)
ACTION=$(python3 - <<'PY'
import html,re
page=open('/tmp/kc_auth.html',encoding='utf-8',errors='replace').read()
m=re.search(r'<form[^>]+id="kc-form-login"[^>]*action="([^"]+)"', page, re.I)
if not m:
    m=re.search(r'<form[^>]*action="([^"]+)"', page, re.I)
if not m:
    raise SystemExit('NO_FORM_ACTION')
print(html.unescape(m.group(1)))
PY
)
echo "ACTION=$ACTION"

# 3) POST login; do NOT follow redirect to 8081; capture Location
# Use -c/-b so AUTH_SESSION cookies are sent
HTTP_CODE=$(curl -sS -c "$CJ" -b "$CJ" -o /tmp/kc_post.body -D /tmp/kc_post.hdr -w '%{http_code}' \
  -X POST "$ACTION" \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -H "Origin: $BASE" \
  --data-urlencode "username=$USER" \
  --data-urlencode "password=$PASS" \
  --data-urlencode 'credentialId=')
echo "POST_HTTP=$HTTP_CODE"
echo "COOKIES_AFTER_POST:"
cat "$CJ" || true
echo "--- HEADERS ---"
head -40 /tmp/kc_post.hdr
LOC=$(grep -i '^Location:' /tmp/kc_post.hdr | tail -1 | sed 's/[Ll]ocation: //;s/\r//')
echo "LOCATION=$LOC"

# If 200 and still a form / required action, try to continue once
if [ -z "$LOC" ]; then
  if grep -q 'required-action\|Update profile\|Update Account' /tmp/kc_post.body; then
    echo "HIT_REQUIRED_ACTION"
    ACTION2=$(python3 - <<'PY'
import html,re
page=open('/tmp/kc_post.body',encoding='utf-8',errors='replace').read()
m=re.search(r'<form[^>]*action="([^"]+)"', page, re.I)
print(html.unescape(m.group(1)) if m else '')
PY
)
    if [ -n "$ACTION2" ]; then
      HTTP_CODE=$(curl -sS -c "$CJ" -b "$CJ" -o /tmp/kc_post.body -D /tmp/kc_post.hdr -w '%{http_code}' \
        -X POST "$ACTION2" \
        -H 'Content-Type: application/x-www-form-urlencoded' \
        --data-urlencode 'email=j.reyes@meridian.local' \
        --data-urlencode 'firstName=J' \
        --data-urlencode 'lastName=Reyes' \
        --data-urlencode "username=$USER")
      echo "REQ_POST_HTTP=$HTTP_CODE"
      LOC=$(grep -i '^Location:' /tmp/kc_post.hdr | tail -1 | sed 's/[Ll]ocation: //;s/\r//')
      echo "LOCATION2=$LOC"
    fi
  fi
fi

# Extract code
CODE=$(python3 - <<PY
import urllib.parse,re,os
loc=os.environ.get('LOC','')
PY
)
CODE=$(LOC="$LOC" python3 - <<'PY'
import os,urllib.parse,re
loc=os.environ.get("LOC","")
body=open("/tmp/kc_post.body",encoding="utf-8",errors="replace").read()
for src in (loc, body):
    qs=urllib.parse.parse_qs(urllib.parse.urlparse(src).query)
    if qs.get("code"):
        print(qs["code"][0]); raise SystemExit
    m=re.search(r'[?&]code=([^&\s"\']+)', src or "")
    if m:
        print(urllib.parse.unquote(m.group(1))); raise SystemExit
print("")
PY
)
echo "CODE=${CODE:0:60}"
if [ -z "$CODE" ]; then
  echo "BODY_SNIP:"
  head -c 500 /tmp/kc_post.body; echo
  # dump cookie/error clue
  grep -i 'Cookie not found\|Invalid\|error' /tmp/kc_post.body | head -5 || true
  exit 2
fi

# 4) Token exchange with code_verifier
curl -sS -c "$CJ" -b "$CJ" -o /home/wazuh/token_response_pkce.json \
  -X POST "$BASE/realms/meridian/protocol/openid-connect/token" \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'grant_type=authorization_code' \
  --data-urlencode "client_id=$CLIENT" \
  --data-urlencode "code=$CODE" \
  --data-urlencode "redirect_uri=$REDIRECT" \
  --data-urlencode "code_verifier=$VERIFIER"

python3 - <<'PY'
import json,base64
tok=open("/home/wazuh/token_response_pkce.json",encoding="utf-8").read()
data=json.loads(tok)
assert "access_token" in data and "id_token" in data, data
print("KEYS", sorted(data.keys()))
def dec(p):
    p += "=" * (-len(p)%4)
    return json.dumps(json.loads(base64.urlsafe_b64decode(p)), indent=2)
h,p,*_=data["access_token"].split(".")
open("/home/wazuh/jwt_decode_pkce.txt","w").write(
  "Evidence #8 â€“ decoded access_token (authorization_code + PKCE S256 via curl)\nHEADER:\n"+dec(h)+"\n\nPAYLOAD:\n"+dec(p)+"\n"
)
open("/home/wazuh/pkce_meta.txt","w").write("grant=authorization_code\npkce=S256\ntransport=curl-cookie-jar\n")
print("PKCE_TOKEN_OK")
PY
'''


def run(c, cmd, t=180):
    print(">>>", cmd[:120], flush=True)
    chan = c.get_transport().open_session()
    chan.settimeout(t)
    chan.exec_command(cmd)
    out, err = b"", b""
    while True:
        if chan.recv_ready():
            out += chan.recv(65535)
        if chan.recv_stderr_ready():
            err += chan.recv_stderr(65535)
        if chan.exit_status_ready():
            while chan.recv_ready():
                out += chan.recv(65535)
            while chan.recv_stderr_ready():
                err += chan.recv_stderr(65535)
            break
        time.sleep(0.1)
    text = out.decode(errors="replace")
    et = err.decode(errors="replace")
    code = chan.recv_exit_status()
    print(text[-3500:] if len(text) > 3500 else text, flush=True)
    if et:
        print("ERR", et[-800:], flush=True)
    print("exit", code, flush=True)
    return text, et, code


def sudo(c, inner, t=120):
    return run(c, "printf '%s\\n' '%s' | sudo -S -p '' bash -lc %s" % (PW, PW, json.dumps(inner)), t)


def main():
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect("127.0.0.1", 2223, username="wazuh", password=PW, timeout=40, allow_agent=False, look_for_keys=False)
    c.get_transport().set_keepalive(30)
    sudo(c, "docker start keycloak || true")
    for _ in range(15):
        o, _, _ = run(c, "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8080/")
        if "200" in o or "302" in o:
            break
        time.sleep(3)

    # refresh user password + clear required actions
    sudo(
        c,
        "docker exec keycloak /opt/keycloak/bin/kcadm.sh config credentials "
        "--server http://localhost:8080 --realm master --user admin --password admin",
    )
    sudo(
        c,
        "docker exec keycloak /opt/keycloak/bin/kcadm.sh update "
        "authentication/required-actions/VERIFY_PROFILE -r meridian -s enabled=false || true",
    )
    out, _, _ = sudo(
        c,
        "docker exec keycloak /opt/keycloak/bin/kcadm.sh get users -r meridian "
        "-q username=j.reyes --fields id --format csv --noquotes",
    )
    uid = [ln.strip() for ln in out.splitlines() if ln.strip() and "id" not in ln.lower() and len(ln.strip()) > 8][-1]
    patch = json.dumps({
        "email": "j.reyes@meridian.local",
        "emailVerified": True,
        "firstName": "J",
        "lastName": "Reyes",
        "requiredActions": [],
        "enabled": True,
    })
    sftp = c.open_sftp()
    with sftp.file("/tmp/user_patch.json", "w") as f:
        f.write(patch)
    with sftp.file("/home/wazuh/pkce_curl.sh", "w") as f:
        f.write(REMOTE_SH)
    sftp.close()
    sudo(
        c,
        f"docker cp /tmp/user_patch.json keycloak:/tmp/user_patch.json && "
        f"docker exec keycloak /opt/keycloak/bin/kcadm.sh update users/{uid} -r meridian -f /tmp/user_patch.json && "
        f"docker exec keycloak /opt/keycloak/bin/kcadm.sh set-password -r meridian --userid {uid} --new-password ClinicalUser2026!",
    )

    out, err, code = run(c, "chmod +x /home/wazuh/pkce_curl.sh && bash /home/wazuh/pkce_curl.sh", 120)
    if "PKCE_TOKEN_OK" not in out:
        c.close()
        raise SystemExit("curl PKCE failed")

    sftp = c.open_sftp()
    sftp.get("/home/wazuh/token_response_pkce.json", os.path.join(EV, "ev7_token_response.json"))
    sftp.get("/home/wazuh/jwt_decode_pkce.txt", os.path.join(EV, "ev8_jwt_decode.txt"))
    try:
        sftp.get("/home/wazuh/pkce_meta.txt", os.path.join(EV, "ev7_pkce_meta.txt"))
    except Exception:
        pass
    sftp.close()
    c.close()

    tok = json.load(open(os.path.join(EV, "ev7_token_response.json"), encoding="utf-8"))
    pretty = {
        "grant": "authorization_code + PKCE S256 (curl cookie jar)",
        "token_type": tok.get("token_type"),
        "expires_in": tok.get("expires_in"),
        "refresh_expires_in": tok.get("refresh_expires_in"),
        "scope": tok.get("scope"),
        "access_token": (tok.get("access_token") or "")[:100] + "...",
        "refresh_token": (tok.get("refresh_token") or "")[:100] + "...",
        "id_token": (tok.get("id_token") or "")[:100] + "...",
    }
    ev7 = (
        "Evidence #7 â€“ token_response.json (authorization_code + PKCE S256)\n"
        "Keys: " + ", ".join(sorted(tok.keys())) + "\n\n"
        + json.dumps(pretty, indent=2)
    )
    open(os.path.join(EV, "ev7_token_pretty.txt"), "w", encoding="utf-8").write(ev7)
    ev8 = open(os.path.join(EV, "ev8_jwt_decode.txt"), encoding="utf-8").read()

    def render(title, body, path, h=820):
        img = Image.new("RGB", (1100, h), (18, 22, 28))
        d = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("consola.ttf", 16)
            fb = ImageFont.truetype("consola.ttf", 18)
        except Exception:
            font = fb = ImageFont.load_default()
        d.text((24, 16), title, fill=(90, 180, 255), font=fb)
        y = 50
        for line in body.splitlines():
            if y > h - 28:
                break
            d.text((24, y), line[:125], fill=(220, 220, 220), font=font)
            y += 20
        img.save(path)
        print("wrote", path)

    render("Evidence #7 â€“ Keycloak tokens (authorization_code + PKCE)", ev7, os.path.join(FIG, "fig_ev7.png"))
    render("Evidence #8 â€“ decoded JWT (PKCE auth-code)", ev8, os.path.join(FIG, "fig_ev8.png"), h=900)
    print("PKCE_CURL_DONE")


if __name__ == "__main__":
    main()
