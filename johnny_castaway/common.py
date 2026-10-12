import json
import os
from pathlib import Path
import subprocess
import shutil

APP = Path(__file__).resolve().parent.parent
CONFIG = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'johnny-castaway' / 'settings.json'
ENGINE_CONFIG = Path(os.environ.get('XDG_STATE_HOME', Path.home() / '.local/state')) / 'wilson-reborn' / 'config.txt'
SERVICE = 'johnny-castaway-idle.service'
DEFAULTS = {'minutes': 5, 'muted': True, 'windowed': False, 'speed': 100,
            'scale': 'fit', 'filter': 'linear', 'dedither': False, 'daynight': 'original'}
CHOICES = {'scale': ('fit', 'stretch', 'integer', 'extend'),
           'filter': ('nearest', 'linear', 'xbr', 'xbrz'),
           'daynight': ('original', 'real24h')}

def validate_settings(value):
    if not isinstance(value, dict):
        raise ValueError('Settings must be an object')
    settings = DEFAULTS.copy()
    settings.update({key: value[key] for key in DEFAULTS if key in value})
    for key, low, high in (('minutes', 1, 240), ('speed', 25, 400)):
        if type(settings[key]) is not int or not low <= settings[key] <= high:
            raise ValueError(f'{key.capitalize()} must be between {low} and {high}')
    for key in ('muted', 'windowed', 'dedither'):
        if type(settings[key]) is not bool:
            raise ValueError(f'Invalid {key} setting')
    for key, choices in CHOICES.items():
        if settings[key] not in choices:
            raise ValueError(f'Invalid {key} setting')
    return settings

def load_settings():
    try:
        return validate_settings(json.loads(CONFIG.read_text()))
    except FileNotFoundError:
        return DEFAULTS.copy()

def save_settings(minutes, muted, options=None):
    settings = load_settings()
    settings.update(options or {})
    settings.update(minutes=minutes, muted=muted)
    settings = validate_settings(settings)
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    temporary = CONFIG.with_suffix('.tmp')
    temporary.write_text(json.dumps(settings, indent=2) + '\n')
    temporary.replace(CONFIG)

def prepare_engine_config(settings):
    """Set managed options, including false booleans; preserve story/other settings.

    Upstream CLI has only enabling flags for windowed/mute/dedither, so omitting
    a flag cannot turn off a true value already saved in its config file.
    """
    settings = validate_settings(settings)
    values = {key: settings[key] for key in ('windowed', 'speed', 'scale', 'filter', 'dedither', 'daynight')}
    values['mute'] = settings['muted']
    values = {key: str(value).lower() if isinstance(value, bool) else str(value)
              for key, value in values.items()}
    try:
        lines = ENGINE_CONFIG.read_text().splitlines()
    except FileNotFoundError:
        lines = []
    updated = []
    seen = set()
    for line in lines:
        key = line.split('=', 1)[0].strip() if '=' in line else None
        if key in values:
            updated.append(f'{key}={values[key]}')
            seen.add(key)
        else:
            updated.append(line)
    updated.extend(f'{key}={value}' for key, value in values.items() if key not in seen)
    ENGINE_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    temporary = ENGINE_CONFIG.with_suffix('.tmp')
    temporary.write_text('\n'.join(updated) + '\n')
    temporary.replace(ENGINE_CONFIG)

def command(muted=False, settings=None):
    settings = validate_settings(load_settings() if settings is None else settings)
    args = [str(APP / 'wilson'), '--data', str(APP / 'data'),
            '--speed', str(settings['speed']), '--scale', settings['scale'],
            '--filter', settings['filter'], '--daynight', settings['daynight']]
    if muted:
        args.append('--mute')
    if settings['windowed']:
        args.append('--windowed')
    if settings['dedither']:
        args.append('--dedither')
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
