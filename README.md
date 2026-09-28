# HuDy Tool Rejoin

Tool Rejoin for Termux with HuDy WebKey authorization backed by Cloudflare D1.

## Install

Use a current Termux release from F-Droid or the official Termux GitHub releases. The Play Store build is obsolete and can contain incompatible TLS packages.

```bash
bash <(curl -fLs https://raw.githubusercontent.com/huuduydz/HuDy_Tool/refs/heads/main/setup.sh)
```

The installer synchronizes Termux packages, verifies the administrator-issued Rejoin key, validates the downloaded Python file, and installs the `hudy` command.

## Repair a broken curl installation

If `curl` reports `CANNOT LINK EXECUTABLE` or a missing `SSL_*` symbol, repair the partial Termux upgrade first:

```bash
pkg update -y
pkg upgrade -y
pkg reinstall openssl libcurl curl -y
hash -r
```

Then run the installer command again. If `pkg` cannot repair the packages, install the current Termux app from F-Droid or GitHub; do not use the obsolete Play Store build.

After installation, run:

```bash
hudy
```

`hudy.py` requests the key on every launch. It performs one authorization request at startup and does not run a periodic WebKey heartbeat.
