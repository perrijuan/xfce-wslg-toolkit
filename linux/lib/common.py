"""Shared, validated configuration for the portable WSLg toolkit."""
import json
import os
from pathlib import Path, PureWindowsPath
import re

DEFAULTS = {
    'refresh_rate': 144,
    'adapter': 'auto',
    'windowed': True,
    'window_title': 'Xfce WSL',
    'nested_display': ':20',
    'host_display': ':0',
    'auto_focus': True,
    'windows_helper_dir': None,
    'powershell_wsl': '/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe',
}

def load_config(path=None):
    """Read local JSON configuration. Invalid input never silently changes policy."""
    if path is None:
        directory = Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home()/'.config')))
        path = directory/'xfce-wsl/config.json'
    else:
        path = Path(path)
    config = dict(DEFAULTS)
    if path.exists():
        data = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(data, dict):
            raise ValueError('Configuration must be a JSON object')
        config.update(data)
    rate = config['refresh_rate']
    if isinstance(rate, bool) or not isinstance(rate, int) or not 1 <= rate <= 144:
        raise ValueError('refresh_rate must be an integer between 1 and 144')
    for key in ('windowed', 'auto_focus'):
        if not isinstance(config[key], bool):
            raise ValueError(key+' must be boolean')
    if not isinstance(config['window_title'], str) or not config['window_title'].strip():
        raise ValueError('window_title must not be empty')
    for key in ('nested_display', 'host_display'):
        if not isinstance(config[key], str) or not re.fullmatch(r':\d+(?:\.\d+)?', config[key]):
            raise ValueError(key+' must be a local X11 display')
    if config['nested_display'].split('.')[0] == config['host_display'].split('.')[0]:
        raise ValueError('Host and nested displays must be distinct')
    if not isinstance(config['adapter'], str) or len(config['adapter']) > 256:
        raise ValueError('adapter must be a short string')
    return config

def toolkit_root():
    return Path(__file__).resolve().parents[1]

def windows_command(script, config=None):
    """Build argv without a shell; spaces and clipboard content are never commands."""
    if script not in ('clipboard-host.ps1', 'Focus-Xfce.ps1'):
        raise ValueError('Unsupported Windows helper')
    config = load_config() if config is None else config
    directory = config.get('windows_helper_dir')
    if not isinstance(directory, str) or not PureWindowsPath(directory).is_absolute():
        raise ValueError('Run the Windows setup step to configure windows_helper_dir')
    executable = config.get('powershell_wsl')
    if not isinstance(executable, str) or not executable.startswith('/'):
        raise ValueError('powershell_wsl must be an absolute Linux interop path')
    return [executable, '-NoLogo', '-NoProfile', '-NonInteractive', '-STA',
            '-ExecutionPolicy', 'Bypass', '-File', str(PureWindowsPath(directory)/script)]

def renderer_info(output):
    renderer = next((line.split(':', 1)[1].strip() for line in output.splitlines()
                     if 'OpenGL renderer string:' in line), 'unknown')
    accelerated = bool(re.search(r'^\s*Accelerated:\s*yes\s*$', output, re.M))
    return {'renderer': renderer, 'accelerated': accelerated and 'llvmpipe' not in renderer.lower()}

def select_monitor(monitors, side):
    if not monitors or side not in ('left', 'right'):
        raise ValueError('A connected monitor and left/right are required')
    ordered = sorted(monitors, key=lambda monitor: (monitor['x'], monitor['y']))
    return ordered[0 if side == 'left' else -1]

def window_rect(current, monitor):
    """Keep a resizable window inside a selected monitor with room for borders."""
    width=min(current['WIDTH'],max(160,monitor['width']-80))
    height=min(current['HEIGHT'],max(160,monitor['height']-120))
    return dict(X=monitor['x']+(monitor['width']-width)//2,
                Y=monitor['y']+(monitor['height']-height)//2,
                WIDTH=width,HEIGHT=height)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--get', choices=('refresh_rate', 'fullscreen'), required=True)
    option = parser.parse_args().get
    config = load_config()
    print(config['refresh_rate'] if option == 'refresh_rate' else int(not config['windowed']))
