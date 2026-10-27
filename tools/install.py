#!/usr/bin/env python3
"""Install the portable toolkit as the normal WSL user; apt alone uses sudo."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'linux/lib'))
from common import load_config

PACKAGES=['xfce4','xfce4-terminal','xfce4-notifyd','xfce4-pulseaudio-plugin',
          'mousepad','ristretto','tumbler','xfdesktop4-data',
          'greybird-gtk-theme','elementary-xfce-icon-theme','adwaita-icon-theme',
          'xserver-xephyr','bubblewrap','dbus-x11','xauth','x11-utils',
          'x11-xserver-utils','xdotool','mesa-utils','python3','python3-gi','gir1.2-gtk-3.0']
COMMANDS=['xfce-wsl','xfce-wsl-display','xfce-wsl-restore-cursor','xfce-wsl-run']
BEGIN='# BEGIN XFCE WSLG TOOLKIT'
END='# END XFCE WSLG TOOLKIT'

def refresh(value):
    value=int(value)
    if not 1<=value<=144:raise argparse.ArgumentTypeError('refresh rate must be 1..144')
    return value

def managed_block(text,body):
    block=BEGIN+'\n'+body.rstrip()+'\n'+END
    if BEGIN in text:
        before,tail=text.split(BEGIN,1)
        if END not in tail:raise ValueError('Incomplete managed alias block; repair it before installing')
        _old,after=tail.split(END,1)
        return before+block+after
    return text.rstrip()+'\n\n'+block+'\n'

def desktop_entry(program,name):
    # Desktop Entry Exec uses double-quote escaping, not shell quoting.
    quoted='"'+str(program).replace('\\','\\\\').replace('"','\\"').replace('%','%%')+'"'
    return '[Desktop Entry]\nType=Application\nName='+name+'\nExec=/usr/bin/python3 '+quoted+'\nOnlyShowIn=XFCE;\nTerminal=false\nStartupNotify=false\n'

def wallpaper_xml():
    channel=ET.Element('channel',name='xfce4-desktop',version='1.0')
    backdrop=ET.SubElement(channel,'property',name='backdrop',type='empty')
    screen=ET.SubElement(backdrop,'property',name='screen0',type='empty')
    backgrounds=Path('/usr/share/backgrounds/xfce')
    image=next((p for p in sorted(backgrounds.glob('*')) if p.suffix.lower() in ('.jpg','.jpeg','.png','.svg')),None)
    for name in ('monitor0','monitordefault'):
        monitor=ET.SubElement(screen,'property',name=name,type='empty')
        workspace=ET.SubElement(monitor,'property',name='workspace0',type='empty')
        ET.SubElement(workspace,'property',name='image-style',type='int',value='5' if image is not None else '0')
        ET.SubElement(workspace,'property',name='color-style',type='int',value='0')
        color=ET.SubElement(workspace,'property',name='rgba1',type='array')
        for value in ('0.08','0.15','0.24','1.0'):ET.SubElement(color,'value',type='double',value=value)
        if image is not None:ET.SubElement(workspace,'property',name='last-image',type='string',value=str(image))
    return ET.tostring(channel,encoding='unicode')+'\n'

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run',action='store_true')
    parser.add_argument('--skip-packages',action='store_true')
    parser.add_argument('--skip-windows',action='store_true')
    parser.add_argument('--no-alias',action='store_true')
    parser.add_argument('--create-shortcut',action='store_true')
    parser.add_argument('--prefix',type=Path)
    parser.add_argument('--refresh-rate',type=refresh)
    parser.add_argument('--adapter')
    args=parser.parse_args()
    home=Path(os.environ.get('HOME') or Path.home()).expanduser().resolve()
    prefix=(args.prefix or home/'.local/share/xfce-wslg-toolkit').expanduser().resolve()
    if prefix in (Path(prefix.anchor),home,home.parent):parser.error('Use a dedicated toolkit directory, not HOME or a filesystem root')
    config_home=Path(os.environ.get('XDG_CONFIG_HOME',str(home/'.config')))
    config_path=config_home/'xfce-wsl/config.json'
    config=load_config(config_path)
    if args.refresh_rate is not None:config['refresh_rate']=args.refresh_rate
    if args.adapter is not None:config['adapter']=args.adapter
    plan={'dry_run':args.dry_run,'prefix':str(prefix),'packages':PACKAGES,
          'package_install':not args.skip_packages,'windows_setup':not args.skip_windows,
          'aliases':not args.no_alias,'create_shortcut':args.create_shortcut,
          'refresh_rate':config['refresh_rate'],'windowed':config['windowed'],
          'runtime_files':[str(p.relative_to(ROOT/'linux')) for p in sorted((ROOT/'linux').rglob('*')) if p.is_file() and '__pycache__' not in p.parts]}
    if args.dry_run:
        print(json.dumps(plan,indent=2,ensure_ascii=False));return 0
    if not sys.platform.startswith('linux'):parser.error('Run installation inside WSL Ubuntu; --dry-run is cross-platform')
    if os.geteuid()==0:parser.error('Run as your normal WSL user, not root; sudo is used only for apt')
    if not args.skip_packages:
        if not shutil.which('apt-get'):parser.error('The package installation path requires Ubuntu/Debian apt-get')
        subprocess.run(['sudo','apt-get','update'],check=True)
        subprocess.run(['sudo','apt-get','--simulate','install','--no-install-recommends',*PACKAGES],check=True)
        subprocess.run(['sudo','apt-get','install','--yes','--no-install-recommends',*PACKAGES],check=True)
    if not args.skip_windows:
        powershell=shutil.which('powershell.exe')
        if not powershell:parser.error('Windows PowerShell interop is unavailable; use --skip-windows only for staging or an existing setup')
        setup=subprocess.check_output(['wslpath','-w',str(ROOT/'windows/Setup-Windows.ps1')],text=True).strip()
        command=[powershell,'-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',setup,'-RefreshRate',str(config['refresh_rate'])]
        if args.create_shortcut:
            import pwd
            command+=['-CreateShortcut','-Distro',os.environ.get('WSL_DISTRO_NAME','Ubuntu'),'-LinuxUser',pwd.getpwuid(os.getuid()).pw_name,'-LinuxLauncher',str(home/'.local/bin/xfce-wsl')]
        completed=subprocess.run(command,text=True,encoding='utf-8',capture_output=True,check=True)
        result=json.loads(completed.stdout)
        if result.get('changed',False) and not result.get('applied',False):raise RuntimeError('Windows setup did not apply the requested configuration')
        config['windows_helper_dir']=result['windows_helper_dir']
        config['powershell_wsl']=subprocess.check_output(['wslpath','-u',result['powershell_windows']],text=True).strip()
    changed=[]
    backup_root=home/'.local/state/xfce-wslg-toolkit/backups'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    def backup(path):
        if path.exists() or path.is_symlink():
            backup_root.mkdir(parents=True,exist_ok=True)
            target=backup_root/(str(path.relative_to(home)).replace('/','__') if path.is_relative_to(home) else path.name)
            if path.is_symlink():target.write_text(str(path.readlink()))
            else:shutil.copy2(path,target)
    def write(path,data,mode=0o644):
        data=data.encode('utf-8') if isinstance(data,str) else data
        if path.is_file() and not path.is_symlink() and path.read_bytes()==data:return
        backup(path);path.parent.mkdir(parents=True,exist_ok=True)
        if path.is_symlink():path.unlink()
        path.write_bytes(data);path.chmod(mode);changed.append(str(path))
    for source in sorted((ROOT/'linux').rglob('*')):
        if not source.is_file() or '__pycache__' in source.parts:continue
        relative=source.relative_to(ROOT/'linux')
        write(prefix/relative,source.read_bytes(),0o755 if relative.parts[0]=='bin' else 0o644)
    commands=home/'.local/bin';commands.mkdir(parents=True,exist_ok=True)
    for name in COMMANDS:
        destination=commands/name;target=prefix/'bin'/name
        if destination.is_symlink() and destination.resolve()==target.resolve():continue
        backup(destination)
        if destination.exists() or destination.is_symlink():destination.unlink()
        destination.symlink_to(target);changed.append(str(destination))
    write(config_path,json.dumps(config,indent=2,ensure_ascii=False)+'\n')
    xml_dir=config_home/'xfce4/xfconf/xfce-perchannel-xml'
    for source in sorted((ROOT/'config/xfce').glob('*.xml')):
        destination=xml_dir/source.name
        if not destination.exists():write(destination,source.read_bytes())
    if not (xml_dir/'xfce4-desktop.xml').exists():write(xml_dir/'xfce4-desktop.xml',wallpaper_xml())
    startup=config_home/'autostart'
    write(startup/'xfce-wsl-wallpaper-bridge.desktop',desktop_entry(prefix/'lib/wallpaper-bridge.py','Xfce WSL wallpaper compatibility'))
    if config.get('windows_helper_dir'):
        write(startup/'xfce-wsl-clipboard.desktop',desktop_entry(prefix/'lib/clipboard-bridge.py','Xfce WSL native text clipboard'))
    if not args.no_alias:
        aliases=home/'.bash_aliases'
        text=aliases.read_text() if aliases.exists() else ''
        body='alias xfce="$HOME/.local/bin/xfce-wsl"\nalias xfce144=\'XFCE_WSL_REFRESH_RATE=144 "$HOME/.local/bin/xfce-wsl"\''
        write(aliases,managed_block(text,body))
        bashrc=home/'.bashrc';text=bashrc.read_text() if bashrc.exists() else ''
        if '.bash_aliases' not in text:write(bashrc,text.rstrip()+'\n\n[ ! -f "$HOME/.bash_aliases" ] || . "$HOME/.bash_aliases"\n')
    report={'installed':True,'prefix':str(prefix),'config':str(config_path),'changed_files':changed,
            'windows_setup_skipped':args.skip_windows,'packages_skipped':args.skip_packages,
            'restart_required_for_wslg':not args.skip_windows,
            'note':'No WSL restart was performed. Save work before restarting WSL manually.'}
    print(json.dumps(report,indent=2,ensure_ascii=False));return 0

if __name__=='__main__':
    try:raise SystemExit(main())
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as error:
        print('Installation failed: '+str(error),file=sys.stderr);raise SystemExit(1)
