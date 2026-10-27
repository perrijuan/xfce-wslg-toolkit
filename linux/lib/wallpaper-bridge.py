#!/usr/bin/python3
"""Bridge Xfce 4.20 numeric settings to Xephyr's named monitor."""
from pathlib import Path
import fcntl,os,re,signal,subprocess,hashlib
from gi.repository import Gio,GLib,GLibUnix
runtime=Path(os.environ.get('XDG_RUNTIME_DIR','/run/user/'+str(os.getuid())))
# A previous private D-Bus can outlive its desktop. Never block another session.
session_key=hashlib.sha256(os.environ['DBUS_SESSION_BUS_ADDRESS'].encode()).hexdigest()[:16]
lock=(runtime/('xfce-wsl-wallpaper-bridge-'+session_key+'.lock')).open('w')
try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
except BlockingIOError:raise SystemExit(0)
outputs=[line.split()[0] for line in subprocess.check_output(['xrandr','--query'],text=True).splitlines() if ' connected' in line]
if len(outputs)!=1 or outputs[0]=='0':raise SystemExit('Bridge is only intended for a single nested Xephyr output')
numeric='/backdrop/screen0/monitor0/'
named='/backdrop/screen0/monitor'+outputs[0]+'/'
channel='xfce4-desktop'
bus=Gio.bus_get_sync(Gio.BusType.SESSION,None)
proxy=Gio.DBusProxy.new_sync(bus,Gio.DBusProxyFlags.NONE,None,'org.xfce.Xfconf','/org/xfce/Xfconf','org.xfce.Xfconf',None)
loop=GLib.MainLoop()
def get(prop):
 try:return proxy.call_sync('GetProperty',GLib.Variant('(ss)',(channel,prop)),Gio.DBusCallFlags.NONE,2000,None).get_child_value(0).get_variant()
 except GLib.Error:return None
def set_value(prop,value):
 current=get(prop)
 if current is None or not current.equal(value):
  proxy.call_sync('SetProperty',GLib.Variant('(ssv)',(channel,prop,value)),Gio.DBusCallFlags.NONE,2000,None)
def changed(_proxy,_sender,name,params):
 if name!='PropertyChanged' or params.get_child_value(0).get_string()!=channel:return
 prop=params.get_child_value(1).get_string()
 if prop.startswith(numeric+'workspace'):target=named+prop[len(numeric):]
 elif prop.startswith(named+'workspace'):target=numeric+prop[len(named):]
 else:return
 try:set_value(target,params.get_child_value(2).get_variant())
 except GLib.Error as error:print('Wallpaper sync error:',error,flush=True)
proxy.connect('g-signal',changed)
bus.connect('closed',lambda *_:loop.quit())
# Leave when this desktop ends, even if a stale app keeps its private bus alive.
def session_owner_changed(_bus,_sender,_path,_iface,_signal,params):
 name,old,new=params.unpack()
 if name=='org.xfce.SessionManager' and old and not new:loop.quit()
bus.signal_subscribe('org.freedesktop.DBus','org.freedesktop.DBus','NameOwnerChanged','/org/freedesktop/DBus','org.xfce.SessionManager',Gio.DBusSignalFlags.NONE,session_owner_changed)

for signum in (signal.SIGTERM,signal.SIGINT):GLibUnix.signal_add(GLib.PRIORITY_DEFAULT,signum,lambda: (loop.quit(),False)[1])
# Honour the selection last saved through the actual desktop preferences.
allprops=proxy.call_sync('GetAllProperties',GLib.Variant('(ss)',(channel,numeric.rstrip('/'))),Gio.DBusCallFlags.NONE,3000,None).get_child_value(0)
for index in range(allprops.n_children()):
 pair=allprops.get_child_value(index);prop=pair.get_child_value(0).get_string()
 if prop.startswith(numeric+'workspace'):set_value(named+prop[len(numeric):],pair.get_child_value(1).get_variant())
print('WALLPAPER_BRIDGE_READY',numeric,'<->',named,flush=True)
loop.run()
