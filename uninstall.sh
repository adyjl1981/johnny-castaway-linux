#!/bin/sh
set -eu
if command -v systemctl >/dev/null 2>&1; then
    systemctl --user disable --now johnny-castaway-idle.service || true
fi
config=${XDG_CONFIG_HOME:-"$HOME/.config"}
share=${XDG_DATA_HOME:-"$HOME/.local/share"}
rm -f "$config/systemd/user/johnny-castaway-idle.service" "$share/applications/Johnny-Castaway.desktop"
if command -v systemctl >/dev/null 2>&1; then
    systemctl --user daemon-reload || true
fi
printf '%s\n' 'Idle activation and menu shortcut removed.' "Your data and settings remain in $share/johnny-castaway and $config/johnny-castaway."
