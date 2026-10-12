#!/bin/sh
set -eu
systemctl --user disable --now johnny-castaway-idle.service || true
config=${XDG_CONFIG_HOME:-"$HOME/.config"}
share=${XDG_DATA_HOME:-"$HOME/.local/share"}
rm -f "$config/systemd/user/johnny-castaway-idle.service" "$share/applications/Johnny-Castaway.desktop"
systemctl --user daemon-reload
printf '%s\n' 'Idle activation and menu shortcut removed.' "Your data and settings remain in $share/johnny-castaway and $config/johnny-castaway."
