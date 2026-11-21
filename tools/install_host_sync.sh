#!/usr/bin/env bash
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Run this installer as root" >&2
  exit 1
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
host_root="/var/lib/servio-deployer/public/got"

if ! getent group got-site >/dev/null 2>&1; then
  groupadd --system got-site
fi
if ! id got-site >/dev/null 2>&1; then
  useradd --system --gid got-site --home-dir /nonexistent --no-create-home --shell /usr/sbin/nologin got-site
fi

chgrp got-site /var/lib/servio-deployer
chmod 0710 /var/lib/servio-deployer

install -d -o got-site -g got-site -m 0755 "$host_root"
install -d -o got-site -g got-site -m 0755 "$host_root/releases"
install -o root -g root -m 0755 "$repo_root/ops/got_site_sync.py" /usr/local/libexec/got-site-sync.py
install -o root -g root -m 0644 "$repo_root/ops/systemd/got-site-sync.service" /etc/systemd/system/got-site-sync.service
install -o root -g root -m 0644 "$repo_root/ops/systemd/got-site-sync.timer" /etc/systemd/system/got-site-sync.timer

systemctl daemon-reload
systemctl enable --now got-site-sync.timer
systemctl start got-site-sync.service
systemctl --no-pager --full status got-site-sync.service
