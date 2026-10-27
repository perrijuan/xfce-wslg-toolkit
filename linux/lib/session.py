from pathlib import Path
from common import load_config, toolkit_root
CFG=load_config();ROOT=toolkit_root();NESTED=CFG["nested_display"];HOST=CFG["host_display"]
import subprocess,os,signal,time,json,secrets
state=Path.home()/'.local/state/xfce-wsl'; state.mkdir(parents=True,exist_ok=True)
auth=state/'Xauthority'; auth.touch(mode=0o600,exist_ok=True);auth.chmod(0o600)
subprocess.run(['xauth','-f',str(auth),'add',NESTED,'MIT-MAGIC-COOKIE-1',secrets.token_hex(16)],check=True)
stop=False; children=[]
def stopping(*args):
 global stop
 stop=True
for s in [signal.SIGTERM,signal.SIGINT,signal.SIGHUP]:signal.signal(s,stopping)
try:
 env=dict(os.environ)
 for k in ['WAYLAND_DISPLAY','SESSION_MANAGER','GTK_THEME','GALLIUM_DRIVER','LIBGL_ALWAYS_SOFTWARE','MESA_D3D12_DEFAULT_ADAPTER_NAME','LIBGL_ALWAYS_INDIRECT']:env.pop(k,None)
 # GPU settings remain scoped to this session, never to the user's shell.
 hardware=False; renderer='software requested'; gpu_probe=''
 env.pop('LIBGL_ALWAYS_INDIRECT',None)
 if os.environ.get('XFCE_WSL_GPU','auto')!='software' and Path('/dev/dxg').exists():
  candidate=dict(env,DISPLAY=HOST,GALLIUM_DRIVER='d3d12',MESA_D3D12_DEFAULT_ADAPTER_NAME=('NVIDIA' if CFG['adapter']=='auto' else CFG['adapter']))
  try:
   probe=subprocess.run(['glxinfo','-B'],env=candidate,text=True,capture_output=True,timeout=15)
   gpu_probe=probe.stdout
   hardware=probe.returncode==0 and 'Accelerated: yes' in gpu_probe and 'D3D12 (' in gpu_probe
   if hardware:
    env=candidate
    renderer=next(line.split(':',1)[1].strip() for line in gpu_probe.splitlines() if 'OpenGL renderer string:' in line)
  except (OSError,subprocess.TimeoutExpired):pass
 if not hardware:
  env.update(GALLIUM_DRIVER='llvmpipe',LIBGL_ALWAYS_SOFTWARE='1')
  env.pop('MESA_D3D12_DEFAULT_ADAPTER_NAME',None)
  renderer='llvmpipe - GPU unavailable or software mode selected'
 gpu_info={'accelerated':hardware,'renderer':renderer,'xephyr_glamor':hardware}
 (state/'gpu.json').write_text(json.dumps(gpu_info,indent=2))
 print('XFCE_RENDERER',json.dumps(gpu_info),flush=True)
 # Allocate the initial GPU framebuffer at the target monitor's real size.
 # Enter fullscreen before Xfce/GTK cache their monitor geometry.
 fullscreen_args=[];screen_size='1440x900'
 if os.environ.get('XFCE_WSL_FULLSCREEN','0')=='1':
  monitors=json.loads(subprocess.check_output([str(ROOT/'bin/xfce-wsl-display'),'list'],env=env,text=True,timeout=10))
  monitor=monitors[-1 if os.environ.get('XFCE_WSL_MONITOR','left')=='right' else 0]
  screen_size=str(monitor['width'])+'x'+str(monitor['height'])
  fullscreen_args=[] # Use EWMH below: Xephyr -output crashes with this WSLg build.
 refresh_rate=int(os.environ.get('XFCE_WSL_REFRESH_RATE','144'))
 if not 1<=refresh_rate<=144:raise RuntimeError('XFCE_WSL_REFRESH_RATE must be between 1 and 144')
 print('XFCE_TARGET_REFRESH_HZ',refresh_rate,flush=True)
 server_command=['Xephyr',NESTED,'-fakescreenfps',str(refresh_rate)]+(['-glamor'] if hardware else [])+['-screen',screen_size]+fullscreen_args+['-resizeable','-nolisten','tcp','-auth',str(auth),'-noreset','-no-host-grab','-title',CFG['window_title']]
 server_log=(state/'xephyr.log').open('w')
 server=subprocess.Popen(server_command,env=env,stdout=server_log,stderr=subprocess.STDOUT,start_new_session=True);children.append(server)
 env.update(DISPLAY=NESTED,XAUTHORITY=str(auth),GDK_BACKEND='x11',QT_QPA_PLATFORM='xcb',XDG_CURRENT_DESKTOP='XFCE',XDG_SESSION_DESKTOP='xfce',DESKTOP_SESSION='xfce',XDG_SESSION_TYPE='x11',XDG_MENU_PREFIX='xfce-')
 for i in range(100):
  if server.poll() is not None:raise RuntimeError('Xephyr encerrou')
  if subprocess.run(['xdpyinfo'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:break
  time.sleep(.1)
 else:raise RuntimeError('Display nao ficou pronto')
 if os.environ.get('XFCE_WSL_FULLSCREEN','0')=='1':
  subprocess.run([str(ROOT/'bin/xfce-wsl-display'),os.environ.get('XFCE_WSL_MONITOR','left'),'--startup'],env=env,timeout=40,check=True)
 # Do not restore an obsolete saved 1600x1200 profile over the live
 # Xephyr framebuffer; it leaves xfdesktop's backdrop clipped after resize.
 subprocess.run(['xfconf-query','-c','displays','-p','/AutoEnableProfiles','-s','0'],env=env,check=False)
 subprocess.run(['xfconf-query','-c','displays','-p','/Default/default/Resolution','-s',screen_size],env=env,check=False)
 subprocess.run(['xset','s','off'],env=env)
 subprocess.run(['xset','-dpms'],env=env,stderr=subprocess.DEVNULL)
 subprocess.run(['dbus-update-activation-environment']+[k for k in ['DISPLAY','XAUTHORITY','XDG_CURRENT_DESKTOP','XDG_SESSION_TYPE','GDK_BACKEND','GALLIUM_DRIVER','MESA_D3D12_DEFAULT_ADAPTER_NAME','LIBGL_ALWAYS_SOFTWARE'] if k in env],env=env,check=True)
 session=subprocess.Popen(['xfce4-session'],env=env,start_new_session=True);children.append(session)
 record={'supervisor_pid':os.getpid(),'server_pid':server.pid,'session_pid':session.pid,'env':{k:v for k,v in env.items() if k in ['DISPLAY','XAUTHORITY','DBUS_SESSION_BUS_ADDRESS','XDG_RUNTIME_DIR','XDG_CURRENT_DESKTOP','GDK_BACKEND','QT_QPA_PLATFORM','GALLIUM_DRIVER','MESA_D3D12_DEFAULT_ADAPTER_NAME','LIBGL_ALWAYS_SOFTWARE','XFCE_WSL_REFRESH_RATE']}}
 (state/'session.json').write_text(json.dumps(record,indent=2));(state/'session.json').chmod(0o600)
 subprocess.run(['/usr/bin/python3',str(ROOT/'lib/present.py')],env=env,timeout=60,check=False)
 print('XFCE_WSL_READY',flush=True)
 while not stop and server.poll() is None and session.poll() is None:time.sleep(.3)
finally:
 for p in reversed(children):
  try:os.killpg(p.pid,signal.SIGTERM)
  except ProcessLookupError:pass
 for p in children:
  try:p.wait(timeout=8)
  except subprocess.TimeoutExpired:
   try:os.killpg(p.pid,signal.SIGKILL)
   except ProcessLookupError:pass
 (state/'session.json').unlink(missing_ok=True)
