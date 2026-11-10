#!/usr/bin/env python3
"""Install the built personal niri for the next login, retaining rollback files."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import os
import shutil
import subprocess
import tempfile

root = Path(__file__).resolve().parent.parent
binary = root / "target/release/niri"
if not binary.is_file():
    raise SystemExit("Run ./personal/build.sh first")
subprocess.run([str(binary), "validate"], check=True)
version = subprocess.check_output([str(binary), "--version"], text=True).strip()
commit = subprocess.check_output(["git", "rev-parse", "--short=12", "HEAD"], cwd=root, text=True).strip()
digest = hashlib.file_digest(binary.open("rb"), "sha256").hexdigest()
home = Path.home()
stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
backups = []

def backup(path):
    if path.exists() or path.is_symlink():
        dest = path.with_name(path.name + ".before-personal-" + stamp)
        shutil.copy2(path, dest, follow_symlinks=False)
        backups.append(str(dest))

libexec = home / ".local/libexec"
libexec.mkdir(parents=True, exist_ok=True)
destination = libexec / ("niri-personal-" + commit + "-" + digest[:12])
if destination.exists():
    if hashlib.file_digest(destination.open("rb"), "sha256").hexdigest() != digest:
        raise SystemExit("Existing versioned binary has a different hash")
else:
    shutil.copy2(binary, destination)
    destination.chmod(0o755)

config_home = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config"))
config = config_home / "niri/config.kdl"
text = config.read_text()
binds = config.parent / "custom/personal-floating-snaps.kdl"
binds.parent.mkdir(parents=True, exist_ok=True)
backup(binds)
shutil.copy2(root / "personal/floating-snaps.kdl", binds)
include = 'include "custom/personal-floating-snaps.kdl"'
if include not in text:
    candidate_text = text + "\n// Personal floating-window snap shortcuts.\n" + include + "\n"
    with tempfile.NamedTemporaryFile(mode="w", prefix=".personal-candidate-", dir=config.parent, delete=False) as candidate:
        candidate.write(candidate_text)
        candidate_path = Path(candidate.name)
    subprocess.run([str(binary), "--config", str(candidate_path), "validate"], check=True)
    backup(config)
    shutil.copymode(config, candidate_path)
    os.replace(candidate_path, config)
else:
    subprocess.run([str(binary), "validate"], check=True)

link = libexec / "niri-personal"
backup(link)
temp_link = libexec / (".niri-personal-" + stamp)
temp_link.symlink_to(destination.name)
os.replace(temp_link, link)

override = config_home / "systemd/user/niri.service.d/95-personal.conf"
override.parent.mkdir(parents=True, exist_ok=True)
backup(override)
quoted_path = json.dumps(str(link).replace("%", "%%"))
override.write_text("[Service]\nExecStart=\nExecStart=" + quoted_path + " --session\n")
subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
manifest = {"commit": commit, "sha256": digest, "version": version, "binary": str(destination), "override": str(override), "backups": backups, "activation": "next login"}
state_home = Path(os.environ.get("XDG_STATE_HOME", home / ".local/state"))
state = state_home / "niri-personal" / ("install-" + stamp + ".json")
state.parent.mkdir(parents=True, exist_ok=True)
state.write_text(json.dumps(manifest, indent=2) + "\n")
print(json.dumps(manifest, indent=2))
print("Save work, then log out and log back in. The running compositor was not restarted.")
