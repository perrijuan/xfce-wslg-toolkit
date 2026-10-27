#!/usr/bin/python3
"""Present or inspect the existing nested Xfce session; never start duplicates."""
import argparse,json,os,subprocess,time
from pathlib import Path
import re
from common import load_config, toolkit_root, windows_command
CFG=load_config();ROOT=toolkit_root()
p=argparse.ArgumentParser();p.add_argument('--check-running',action='store_true');p.add_argument('--status',action='store_true');args=p.parse_args()
state=Path.home()/'.local/state/xfce-wsl'
try:
 r=json.loads((state/'session.json').read_text())
 for key in ('supervisor_pid','server_pid','session_pid'):os.kill(r[key],0)
 assert b'Xephyr' in Path('/proc/'+str(r['server_pid'])+'/cmdline').read_bytes()
except (OSError,ValueError,KeyError,AssertionError):
 if not args.check_running:print('Xfce nao esta em execucao.')
 raise SystemExit(3)
if args.check_running:raise SystemExit(0)
env=dict(os.environ);env.update(r['env'])
if args.status:
 print(json.dumps(r,indent=2,ensure_ascii=False))
 probe=subprocess.run(['glxinfo','-B'],env=env,text=True,capture_output=True,timeout=15)
 print('\n'.join(line for line in probe.stdout.splitlines() if any(k in line for k in ['renderer string','Accelerated:','Device:'])))
 raise SystemExit(probe.returncode)
mode='window' if os.environ.get('XFCE_WSL_FULLSCREEN','0')=='0' else os.environ.get('XFCE_WSL_MONITOR','left')
if mode=='window' and os.environ.get('XFCE_WSL_MOVE_MONITOR')=='1':mode='move-'+os.environ.get('XFCE_WSL_MONITOR','left')
helper=ROOT/'bin/xfce-wsl-display'
# Avoid shrinking an already-fullscreen GPU surface just to re-present it.
host=dict(env,DISPLAY=CFG['host_display']);host.pop('XAUTHORITY',None)
requested_monitors=json.loads(subprocess.check_output([str(helper),'list'],env=host,text=True))
requested=requested_monitors[-1 if mode=='right' else 0] if mode in ('left','right') else None
for attempt in range(30):
 status_probe=subprocess.run([str(helper),'status'],env=env,text=True,capture_output=True)
 try:current=json.loads(status_probe.stdout)
 except ValueError:current={}
 already=(requested is not None and '_NET_WM_STATE_FULLSCREEN' in current.get('state','') and current.get('geometry')==dict(X=requested['x'],Y=requested['y'],WIDTH=requested['width'],HEIGHT=requested['height']))
 if mode=='window' and status_probe.returncode==0 and '_NET_WM_STATE_FULLSCREEN' not in current.get('state',''):
  already=True # Preserve the user's current window size and position.
 if already:
  result=status_probe;break
 result=subprocess.run([str(helper),mode],env=env,text=True,capture_output=True)
 if result.returncode==0:break
 time.sleep(.3)
else:raise SystemExit('Nao foi possivel apresentar o Xfce: '+result.stderr[-800:]+result.stdout[-800:])
print(result.stdout,flush=True)
restore=ROOT/'bin/xfce-wsl-restore-cursor'
if restore.exists():subprocess.run([str(restore)],env=env,timeout=10,check=False)
host=dict(env,DISPLAY=CFG['host_display']);host.pop('XAUTHORITY',None)
window=subprocess.check_output(['xdotool','search','--onlyvisible','--name','^'+re.escape(CFG['window_title'])+'$'],env=host,text=True).splitlines()[0]
if CFG['auto_focus']:subprocess.run(['xdotool','windowactivate',window],env=host,timeout=5,check=False)
# Native focus uses the desktop's persistent WSL interop server.
try:
 session_env=dict(item.split(b'=',1) for item in Path('/proc/'+str(r['session_pid'])+'/environ').read_bytes().split(b'\0') if b'=' in item)
 if b'WSL_INTEROP' in session_env:host['WSL_INTEROP']=session_env[b'WSL_INTEROP'].decode()
 focus=subprocess.run(windows_command('Focus-Xfce.ps1',CFG),env=host,text=True,capture_output=True,timeout=15) if CFG['auto_focus'] else None
 if focus is not None:print('Windows focus:',focus.stdout.strip() or focus.stderr[-500:],flush=True)
except (OSError,ValueError,subprocess.TimeoutExpired) as error:print('Native focus warning:',type(error).__name__,flush=True)
print('Xfce apresentado; nenhuma sessao duplicada foi criada.',flush=True)
