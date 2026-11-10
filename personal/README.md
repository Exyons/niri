# Personal niri

Upstream: https://github.com/niri-wm/niri
Fork: https://github.com/Exyons/niri
Personal branch: `personal/stable`, based on upstream **v26.04 / 8ed0da44**.

## Changes

1. Respect holes in floating-window input regions for both pointer targeting and resize targeting. This lets transparent overlay canvases pass clicks to lower windows while retaining server-side borders.
2. `snap-floating-window "bottom-right"` and the corresponding IPC action. Nine anchors: top-left, top, top-right, left, center, right, bottom-left, bottom, bottom-right. Aligns the complete tile, including any border, inside the compositor's output working area. It uses logical coordinates and pixel rounding. Tiled windows are ignored, and `--id` can target an unfocused floating window. Oversized windows keep their top-left accessible rather than moving that corner off-screen.

The compositor change does not shrink an app's transparent canvas or make an app's own broken drag code work. ChatGPT's Linux screen-clamp patch is a separate application compatibility fix.

## Build and install

Dependencies follow upstream `docs/wiki/Development:-Developing-niri.md`.
Run `./personal/build.sh` from an ordinary desktop terminal. The test harness needs working local Unix sockets; an agent sandbox that forbids sockets can hang the Wayland integration tests.
Then run `./personal/install-user.py`. Installation creates a versioned executable under `~/.local/libexec`, links `niri-personal` to it, installs the optional snap bindings, and writes `95-personal.conf` under the user niri service overrides. Save work, log out, and log back in yourself. Installation never restarts the running compositor.

The distro `/usr/bin/niri` stays installed. Its package updates do not replace the selected personal executable. Custom builds need their own upstream update cycle.

## Snap keys

Hold **Super + Alt** and a number on the number row:

| 7 top-left | 8 top | 9 top-right |
|---|---|---|
| 4 left | 5 center | 6 right |
| 1 bottom-left | 2 bottom | 3 bottom-right |

The focused window must already be floating. Super + V uses the existing floating toggle on this desktop (check your current bindings if you change it). `personal/floating-snaps.kdl` uses a spawned IPC command so the existing compositor can still parse the config before the next login; the new action becomes usable after login into the personal build.

CLI example: `~/.local/libexec/niri-personal msg action snap-floating-window bottom-right --id 42`.

## Incorporate the next upstream release

Keep upstream's history and personal changes separate. Do not overwrite the custom binary with an untested upstream build.

```sh
git fetch upstream --tags
# Replace vNEXT and the paths below with the actual next release.
git worktree add -b personal/vNEXT ../niri-vNEXT vNEXT
# List personal commits, oldest first, and cherry-pick them in that new worktree.
git log --reverse --format=%H v26.04..personal/stable
git -C ../niri-vNEXT cherry-pick <personal-commit-1> <personal-commit-2> ...
cd ../niri-vNEXT
./personal/build.sh
./personal/install-user.py
```

If upstream already fixes an issue, inspect the upstream fix and drop the redundant personal commit; if a conflict occurs, resolve it and repeat the relevant regression tests. Update the baseline named in this document to vNEXT. Publish the candidate branch for review, then advance `personal/stable` to that verified candidate through a normal merge. Keep the prior versioned executable for rollback. If you merge upstream instead of cherry-picking onto a new tag, inspect the resulting patch list carefully before the following update.

Only adopt new upstream main commits deliberately if a feature/fix is needed before a release. Stable releases are the default baseline here.

## Roll back

Rename `~/.config/systemd/user/niri.service.d/95-personal.conf` to a filename not ending in `.conf`, run `systemctl --user daemon-reload`, save work, then log out/in. With the earlier `90-pet-input-fix.conf` still enabled, this returns to the previously working custom build. To return all the way to the distro build, also rename that earlier override. Remove the personal-floating-snaps include from the niri config if returning to a compositor that lacks the new action. All installer-created config backups and versioned binaries are retained.
