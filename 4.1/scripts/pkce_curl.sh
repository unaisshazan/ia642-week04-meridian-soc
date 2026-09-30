#!/bin/bash
# Authorization Code + PKCE against Keycloak (curl cookie jar)
set -euo pipefail
export BASE=http://127.0.0.1:8080
export REDIRECT='http://127.0.0.1:8081/callback'
CLIENT=meridian-billing-app
USER=j.reyes
PASS='ClinicalUser2026!'
CJ=/tmp/kc_cj.txt
rm -f "$CJ" /tmp/kc_auth.html /tmp/kc_post.hdr /tmp/kc_post.body /tmp/pkce.json

# Generate verifier/challenge in Python (canonical S256)
python3 - <<'PY'
import base64, hashlib, json, secrets
verifier = secrets.token_urlsafe(64)
# RFC 7636: 43-128 chars
if len(verifier) < 43:
    verifier = (verifier + secrets.token_urlsafe(64))[:64]
elif len(verifier) > 128:
    verifier = verifier[:128]
challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).decode("ascii").rstrip("=")
json.dump({"verifier": verifier, "challenge": challenge}, open("/tmp/pkce.json","w"))
print("VERIFIER_LEN", len(verifier))
print("CHALLENGE", challenge)
PY

VERIFIER=$(python3 -c 'import json;print(json.load(open("/tmp/pkce.json"))["verifier"])')
CHALLENGE=$(python3 -c 'import json;print(json.load(open("/tmp/pkce.json"))["challenge"])')
REDIR_ENC=$(python3 -c 'import urllib.parse,os; print(urllib.parse.quote(os.environ["REDIRECT"], safe=""))')

AUTH_URL="${BASE}/realms/meridian/protocol/openid-connect/auth?client_id=${CLIENT}&response_type=code&scope=openid&redirect_uri=${REDIR_ENC}&code_challenge=${CHALLENGE}&code_challenge_method=S256&state=lab41pkce"
echo "AUTH_URL_OK"

curl -sS -c "$CJ" -b "$CJ" -D /tmp/kc_auth.hdr -o /tmp/kc_auth.html "$AUTH_URL"
echo "COOKIES_GET:"
wc -l "$CJ"
grep -i set-cookie /tmp/kc_auth.hdr | sed 's/Set-Cookie: /SC /;s/;.*//' || true

ACTION=$(python3 - <<'PY'
import html, re
page = open("/tmp/kc_auth.html", encoding="utf-8", errors="replace").read()
m = re.search(r'<form[^>]+id="kc-form-login"[^>]*action="([^"]+)"', page, re.I)
if not m:
    m = re.search(r'<form[^>]*action="([^"]+)"', page, re.I)
if not m:
    raise SystemExit("NO_FORM_ACTION")
print(html.unescape(m.group(1)))
PY
)
echo "ACTION_OK"

HTTP_CODE=$(curl -sS -c "$CJ" -b "$CJ" -o /tmp/kc_post.body -D /tmp/kc_post.hdr -w '%{http_code}' \
  -X POST "$ACTION" \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -H "Origin: ${BASE}" \
  --data-urlencode "username=${USER}" \
  --data-urlencode "password=${PASS}" \
  --data-urlencode 'credentialId=')
echo "POST_HTTP=${HTTP_CODE}"
LOC=$(grep -i '^Location:' /tmp/kc_post.hdr | tail -1 | sed 's/[Ll]ocation: //;s/\r//')
echo "LOCATION=${LOC}"

CODE=$(LOC="$LOC" python3 - <<'PY'
import os, urllib.parse, re
loc = os.environ.get("LOC", "")
qs = urllib.parse.parse_qs(urllib.parse.urlparse(loc).query)
print((qs.get("code") or [""])[0])
PY
)
echo "CODE_PREFIX=${CODE:0:40}"
test -n "$CODE"

# Exchange — same verifier used for challenge
RESP=$(curl -sS -o /home/wazuh/token_response_pkce.json -w '%{http_code}' \
  -X POST "${BASE}/realms/meridian/protocol/openid-connect/token" \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'grant_type=authorization_code' \
  --data-urlencode "client_id=${CLIENT}" \
  --data-urlencode "code=${CODE}" \
  --data-urlencode "redirect_uri=${REDIRECT}" \
  --data-urlencode "code_verifier=${VERIFIER}")
echo "TOKEN_HTTP=${RESP}"
head -c 200 /home/wazuh/token_response_pkce.json; echo

python3 - <<'PY'
import json, base64
data = json.load(open("/home/wazuh/token_response_pkce.json", encoding="utf-8"))
if "error" in data:
    raise SystemExit("TOKEN_ERROR " + json.dumps(data))
assert "access_token" in data and "refresh_token" in data and "id_token" in data
print("KEYS", sorted(data.keys()))

def dec(p):
    p += "=" * (-len(p) % 4)
    return json.dumps(json.loads(base64.urlsafe_b64decode(p)), indent=2)

h, p, *_ = data["access_token"].split(".")
open("/home/wazuh/jwt_decode_pkce.txt", "w").write(
    "Evidence #8 – decoded access_token (authorization_code + PKCE S256)\n"
    "HEADER:\n" + dec(h) + "\n\nPAYLOAD:\n" + dec(p) + "\n"
)
open("/home/wazuh/pkce_meta.txt", "w").write(
    "grant=authorization_code\npkce=S256\ntransport=curl-cookie-jar\n"
)
print("PKCE_TOKEN_OK")
PY
