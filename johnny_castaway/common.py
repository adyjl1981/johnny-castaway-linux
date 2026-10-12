import json
import os
from pathlib import Path
import subprocess
import shutil

APP = Path(__file__).resolve().parent.parent
CONFIG = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'johnny-castaway' / 'settings.json'
SERVICE = 'johnny-castaway-idle.service'
DEFAULTS = {'minutes': 5, 'muted': True}

def load_settings():
    try:
        value = json.loads(CONFIG.read_text())
        minutes = value.get('minutes', 5)
        if isinstance(minutes, bool) or not isinstance(minutes, int) or not 1 <= minutes <= 240:
            raise ValueError('Delay must be between 1 and 240 minutes')
        if not isinstance(value.get('muted', True), bool):
            raise ValueError('Invalid sound setting')
        return {'minutes': minutes, 'muted': value.get('muted', True)}
    except FileNotFoundError:
        return DEFAULTS.copy()

def save_settings(minutes, muted):
    if not 1 <= minutes <= 240:
        raise ValueError('Delay must be between 1 and 240 minutes')
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    temporary = CONFIG.with_suffix('.tmp')
    temporary.write_text(json.dumps({'minutes': minutes, 'muted': muted}, indent=2) + '\n')
    temporary.replace(CONFIG)

def command(muted=False):
    args = [str(APP / 'wilson'), '--data', str(APP / 'data')]
    if muted:
        args.append('--mute')
    return args

def service(action):
    return subprocess.run(['systemctl', '--user', action, SERVICE], check=True,
                          capture_output=True, text=True)


def user_service_available():
    if not shutil.which('systemctl'):
        return False
    try:
        return subprocess.run(['systemctl', '--user', 'show-environment'],
            capture_output=True, timeout=5).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False
