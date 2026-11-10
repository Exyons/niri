#!/usr/bin/env python3
"""Keep only OpenWhispr's floating Voice Recorder on the focused niri workspace."""
import argparse
import json
import os
import socket
import sys
import time


def request(path, message):
    with socket.socket(socket.AF_UNIX) as sock:
        sock.settimeout(3)
        sock.connect(path)
        sock.sendall((json.dumps(message) + "\n").encode())
        with sock.makefile("r", encoding="utf-8") as stream:
            reply = json.loads(stream.readline())
        if "Err" in reply:
            raise RuntimeError(str(reply["Err"]))
        return reply["Ok"]


def moves(workspaces, windows):
    target = next((ws["id"] for ws in workspaces if ws["is_focused"]), None)
    if target is None:
        return []
    return [
        {"Action": {"MoveWindowToWorkspace": {
            "window_id": window["id"], "reference": {"Id": target}, "focus": False,
        }}}
        for window in windows
        if window.get("app_id") == "open-whispr"
        and window.get("title") == "Voice Recorder"
        and window.get("is_floating")
        and window.get("workspace_id") is not None
        and window["workspace_id"] != target
    ]


def sync(path):
    # Query current state instead of replaying old events during rapid switching.
    workspaces = request(path, "Workspaces")["Workspaces"]
    windows = request(path, "Windows")["Windows"]
    actions = moves(workspaces, windows)
    for action in actions:
        request(path, action)
        print("Followed workspace:", json.dumps(action["Action"]), flush=True)
    return len(actions)


def relevant(event):
    if any(key in event for key in ("WorkspacesChanged", "WindowsChanged")):
        return True
    if "WorkspaceActivated" in event:
        return event["WorkspaceActivated"]["focused"]
    window = event.get("WindowOpenedOrChanged", {}).get("window", {})
    return window.get("app_id") == "open-whispr" and window.get("title") == "Voice Recorder"


def watch(path):
    with socket.socket(socket.AF_UNIX) as sock:
        sock.connect(path)
        sock.sendall(b'"EventStream"\n')
        with sock.makefile("r", encoding="utf-8") as stream:
            reply = json.loads(stream.readline())
            if "Err" in reply:
                raise RuntimeError(str(reply["Err"]))
            sync(path)
            print("Watching OpenWhispr workspace changes", flush=True)
            for line in stream:
                if relevant(json.loads(line)):
                    sync(path)
    raise ConnectionError("niri event stream disconnected")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="Reconcile once and exit")
    args = parser.parse_args()
    path = os.environ["NIRI_SOCKET"]
    if args.once:
        print("Moved windows:", sync(path))
        return
    while True:
        try:
            watch(path)
        except (OSError, ValueError, RuntimeError, KeyError) as error:
            print("niri connection:", error, file=sys.stderr, flush=True)
            time.sleep(2)


if __name__ == "__main__":
    main()
