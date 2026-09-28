# HuDy Tool Rejoin

Tool Rejoin for Termux with HuDy WebKey authorization backed by Cloudflare D1.

## Install

Run the installer in Termux. It requests the Rejoin key issued by the HuDy administrator before downloading the tool.

```bash
bash <(curl -fLs https://raw.githubusercontent.com/huuduydz/HuDy_Tool/refs/heads/main/setup.sh)
```

After installation, run:

```bash
hudy
```

`hudy.py` requests the key again on every launch. It performs one authorization request at startup and does not run a periodic WebKey heartbeat.
