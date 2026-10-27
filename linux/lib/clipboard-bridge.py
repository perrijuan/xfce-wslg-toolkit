#!/usr/bin/python3
"""Text clipboard bridge: native Windows sequence -> nested Xfce.
Clipboard text is transmitted only through anonymous process pipes and kept
in memory. No content is logged. Images/files/PRIMARY are not transferred.
"""
import fcntl,hashlib,json,os,signal,subprocess,threading
from pathlib import Path
from common import load_config, windows_command
CFG=load_config()
os.environ['GDK_BACKEND']='x11';os.environ.pop('WAYLAND_DISPLAY',None)
if os.environ.get('DISPLAY','') in ('',':0',':0.0'):
    raise SystemExit('Start through the nested Xfce session.')
key=hashlib.sha256(os.environ['DBUS_SESSION_BUS_ADDRESS'].encode()).hexdigest()[:16]
lockpath=Path(os.environ.get('XDG_RUNTIME_DIR','/run/user/'+str(os.getuid())))/('xfce-wsl-clipboard-'+key+'.lock')
lock=lockpath.open('w');lockpath.chmod(0o600)
try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
except BlockingIOError:raise SystemExit(0)
import gi
gi.require_version('Gtk','3.0');gi.require_version('Gdk','3.0')
from gi.repository import Gtk,Gdk,Gio,GLib,GLibUnix
clipboard=Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
class Bridge:
    def __init__(self):
        self.child=None;self.stopping=False;self.native_seq=None
        self.native_text=None;self.generation=0;self.epoch=0
    def start(self):
        if self.stopping:return False
        if self.child is not None and self.child.poll() is None:return True
        self.epoch+=1;epoch=self.epoch;self.native_seq=None
        command=windows_command('clipboard-host.ps1',CFG)
        child_env=dict(os.environ)
        # A live repair is invoked through a temporary wsl.exe command. Use
        # the desktop's persistent interop server, not that temporary caller.
        try:
            record=json.loads((Path.home()/'.local/state/xfce-wsl/session.json').read_text())
            session_env=dict(item.split(b'=',1) for item in Path('/proc/'+str(record['session_pid'])+'/environ').read_bytes().split(b'\0') if b'=' in item)
            if record['env']['DBUS_SESSION_BUS_ADDRESS']==os.environ['DBUS_SESSION_BUS_ADDRESS'] and b'WSL_INTEROP' in session_env:
                child_env['WSL_INTEROP']=session_env[b'WSL_INTEROP'].decode()
        except (OSError,ValueError,KeyError):pass
        self.child=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=None,text=True,encoding='utf-8',bufsize=1,env=child_env)
        def read(child):
            for line in child.stdout:
                try:message=json.loads(line)
                except (ValueError,TypeError):continue
                GLib.idle_add(self.native_message,epoch,message)
        threading.Thread(target=read,args=(self.child,),daemon=True).start()
        return True
    def native_message(self,epoch,message):
        if self.stopping or epoch!=self.epoch:return False
        kind=message.get('kind')
        if kind not in ('clipboard','ack'):return False
        first=self.native_seq is None
        self.native_seq=message['seq']
        if kind=='clipboard':
            self.generation+=1
            text=message.get('text');self.native_text=text
            if text is not None and len(text.encode('utf-8'))<=8*1024*1024:
                # Always honor a new native sequence, including copying the
                # same text again after the guest lost selection ownership.
                clipboard.set_text(text,-1)
        if first:print('CLIPBOARD_NATIVE_CONNECTED',flush=True)
        return False
    def changed(self,clip,_event):
        self.generation+=1
        clip.request_text(self.guest_text,(self.generation,self.native_seq))
    def guest_text(self,_clip,text,state):
        generation,observed=state
        if self.stopping or generation!=self.generation or observed is None:return
        if text is None or text==self.native_text or len(text.encode('utf-8'))>8*1024*1024:return
        try:
            payload=json.dumps(dict(kind='set',seq=observed,text=text))+'\n'
            self.child.stdin.write(payload);self.child.stdin.flush()
            self.native_text=text
        except (BrokenPipeError,OSError,ValueError):
            self.native_seq=None
    def stop(self):
        self.stopping=True
        if self.child is not None:
            try:self.child.stdin.close()
            except (BrokenPipeError,OSError):pass
            try:self.child.wait(timeout=4)
            except subprocess.TimeoutExpired:self.child.terminate()
        Gtk.main_quit();return False
bridge=Bridge();clipboard.connect('owner-change',bridge.changed)
bus=Gio.bus_get_sync(Gio.BusType.SESSION,None)
def ended(_bus,_sender,_path,_interface,_signal,parameters):
    _name,old,new=parameters.unpack()
    if old and not new:bridge.stop()
bus.signal_subscribe('org.freedesktop.DBus','org.freedesktop.DBus','NameOwnerChanged','/org/freedesktop/DBus','org.xfce.SessionManager',Gio.DBusSignalFlags.NONE,ended)
bus.connect('closed',lambda *_:bridge.stop())
for signum in (signal.SIGTERM,signal.SIGINT):GLibUnix.signal_add(GLib.PRIORITY_DEFAULT,signum,bridge.stop)
bridge.start();GLib.timeout_add_seconds(2,bridge.start)
print('CLIPBOARD_BRIDGE_V2_READY',flush=True)
try:Gtk.main()
finally:
    if not bridge.stopping:bridge.stop()
