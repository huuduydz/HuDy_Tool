#!/data/data/com.termux/files/usr/bin/bash

# HuDy Tool Rejoin installer for Termux.

set -u

C_CYAN="\033[1;36m"
C_GREEN="\033[1;32m"
C_YELLOW="\033[1;33m"
C_RED="\033[1;31m"
C_RESET="\033[0m"

TOOL_URL="https://raw.githubusercontent.com/huuduydz/HuDy_Tool/refs/heads/main/hudy.py"
VERIFY_URL="https://hudyy.com/api/rejoin/verify"
TOOL_PATH="$HOME/hudy.py"
DOWNLOAD_PATH="$HOME/.hudy.py.download.$$"

cleanup() {
    rm -f "$DOWNLOAD_PATH"
    unset HUDY_REJOIN_KEY DEVICE_FP
}
trap cleanup EXIT INT TERM

fail() {
    echo -e "${C_RED}[x] $1${C_RESET}" >&2
    exit 1
}

echo -e "${C_CYAN}[*] Checking the Termux environment...${C_RESET}"

# A partial Termux upgrade can leave curl linked to a newer libcurl but an
# older OpenSSL. Synchronize the complete package set before using curl.
killall -9 apt apt-get dpkg dpkg-deb >/dev/null 2>&1 || true
rm -f "$PREFIX/var/lib/dpkg/lock"*
rm -f "$PREFIX/var/cache/apt/archives/lock"
rm -f "$PREFIX/var/lib/apt/lists/lock"

export DEBIAN_FRONTEND=noninteractive
unset LD_PRELOAD

echo -e "${C_CYAN}[*] Synchronizing Termux packages and TLS libraries...${C_RESET}"
pkg update -y -o Dpkg::Options::="--force-confold" || fail "Unable to update Termux packages. Change your Termux mirror and try again."
pkg upgrade -y -o Dpkg::Options::="--force-confold" || fail "Unable to finish the Termux package upgrade."
pkg install python sqlite tsu ncurses-utils procps openssl libcurl curl -y -o Dpkg::Options::="--force-confold" || fail "Unable to install required packages."
hash -r

if ! curl --version >/dev/null 2>&1; then
    echo -e "${C_YELLOW}[!] curl is still broken. Reinstalling its TLS packages...${C_RESET}"
    apt-get install --reinstall -y openssl libcurl curl >/dev/null 2>&1 || true
    hash -r
fi

curl --version >/dev/null 2>&1 || fail "curl/OpenSSL is still inconsistent. Install the current Termux release from F-Droid or GitHub, then run this installer again."
python --version >/dev/null 2>&1 || fail "Python was not installed correctly."

if [ ! -d "$HOME/storage" ]; then
    echo -e "${C_YELLOW}[!] If Android requests storage access, tap Allow.${C_RESET}"
    termux-setup-storage || true
    sleep 2
fi

printf "${C_YELLOW}[?] Enter the Rejoin key issued by the administrator: ${C_RESET}"
IFS= read -r HUDY_REJOIN_KEY
[ -n "$HUDY_REJOIN_KEY" ] || fail "The key cannot be empty."

DEVICE_FP=""
for DEVICE_PART in "$(settings get secure android_id 2>/dev/null)" "$(getprop ro.serialno 2>/dev/null)" "$(getprop ro.product.model 2>/dev/null)"; do
    case "$DEVICE_PART" in
        ""|null|unknown) ;;
        *) DEVICE_FP="${DEVICE_FP:+${DEVICE_FP}|}${DEVICE_PART}" ;;
    esac
done
DEVICE_FP="${DEVICE_FP:-hudy-rejoin-device}"
export HUDY_REJOIN_KEY DEVICE_FP VERIFY_URL

VERIFY_RESPONSE="$(python - <<'PY'
import json
import os
import urllib.error
import urllib.request

payload = json.dumps({
    "token": os.environ["HUDY_REJOIN_KEY"],
    "fingerprint": os.environ["DEVICE_FP"],
    "deviceName": "Termux installer",
    "version": "installer-2",
}).encode()
request = urllib.request.Request(
    os.environ["VERIFY_URL"],
    data=payload,
    headers={
        "Content-Type": "application/json",
        "User-Agent": "HuDy-Rejoin/installer-2",
    },
)
try:
    with urllib.request.urlopen(request, timeout=20) as response:
        print(response.read().decode("utf-8", "replace"))
except (OSError, urllib.error.URLError):
    print("")
PY
)"
unset HUDY_REJOIN_KEY

printf '%s' "$VERIFY_RESPONSE" | grep -q '"ok":true' || fail "The key is invalid, revoked, out of device slots, or the authorization server is unavailable."
unset VERIFY_RESPONSE DEVICE_FP DEVICE_PART
echo -e "${C_GREEN}[+] Key accepted.${C_RESET}"

echo -e "${C_CYAN}[*] Downloading the latest Tool Rejoin...${C_RESET}"
if ! curl -fL --retry 3 --connect-timeout 15 --max-time 120 "$TOOL_URL" -o "$DOWNLOAD_PATH"; then
    echo -e "${C_YELLOW}[!] curl download failed. Trying Python HTTPS...${C_RESET}"
    export TOOL_URL DOWNLOAD_PATH
    python - <<'PY' || fail "Unable to download Tool Rejoin from GitHub."
import os
import urllib.request

request = urllib.request.Request(
    os.environ["TOOL_URL"],
    headers={"User-Agent": "HuDy-Rejoin/installer-2"},
)
with urllib.request.urlopen(request, timeout=120) as response:
    data = response.read()
if len(data) < 1024:
    raise RuntimeError("Downloaded file is unexpectedly small")
with open(os.environ["DOWNLOAD_PATH"], "wb") as output:
    output.write(data)
PY
fi

[ -s "$DOWNLOAD_PATH" ] || fail "The downloaded hudy.py file is empty."
python - "$DOWNLOAD_PATH" <<'PY' || fail "The downloaded hudy.py file is invalid."
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
compile(path.read_text(encoding="utf-8"), str(path), "exec")
PY
mv -f "$DOWNLOAD_PATH" "$TOOL_PATH"
chmod 700 "$TOOL_PATH"

# Install real commands so they work immediately without reloading .bashrc.
for COMMAND_NAME in hudy hudy4; do
    COMMAND_PATH="$PREFIX/bin/$COMMAND_NAME"
    printf '#!%s/bin/sh\nexec %s/bin/python "%s/hudy.py" "$@"\n' "$PREFIX" "$PREFIX" "$HOME" > "$COMMAND_PATH" || fail "Unable to create the $COMMAND_NAME command."
    chmod 755 "$COMMAND_PATH"
done
hash -r

echo -e "\n${C_GREEN}[+] INSTALLATION COMPLETED SUCCESSFULLY${C_RESET}"
echo -e "${C_YELLOW}[i] Run ${C_CYAN}hudy${C_YELLOW} to start Tool Rejoin.${C_RESET}\n"
