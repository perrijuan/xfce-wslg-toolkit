#!/usr/bin/env python3
"""Capture the real nested desktop as PNG, temporarily hiding apps and file icons.
The original UI state is restored in finally. No clipboard content is read.
"""
import argparse
import binascii
import ctypes as C
import ctypes.util
import json
import os
from pathlib import Path
import re
import signal
import struct
import subprocess
import time
import zlib

def xwd_to_png(data):
    if len(data)<100:raise ValueError('Truncated XWD header')
    h=struct.unpack('>25I',data[:100])
    header,version,format_,depth,width,height=h[:6]
    order,bpp,stride,visual=h[7],h[11],h[12],h[13]
    masks=h[14:17]
    start=header+h[19]*12
    if version!=7 or format_!=2 or bpp not in (24,32) or visual not in (4,5):raise ValueError('Unsupported XWD TrueColor format')
    if not width or not height or width*height>40_000_000 or header<100:raise ValueError('Invalid image dimensions')
    step=bpp//8
    if stride<width*step or len(data)<start+stride*height:raise ValueError('Truncated XWD pixel data')
    channels=[]
    for mask in masks:
        if not mask:raise ValueError('Missing color mask')
        shift=(mask&-mask).bit_length()-1;channels.append((mask,shift,mask>>shift))
    rows=bytearray()
    for y in range(height):
        rows.append(0)
        row=start+y*stride
        for x in range(width):
            pixel=int.from_bytes(data[row+x*step:row+(x+1)*step],'little' if order==0 else 'big')
            rows.extend(((pixel&mask)>>shift)*255//maximum for mask,shift,maximum in channels)
    def chunk(kind,payload):
        return struct.pack('>I',len(payload))+kind+payload+struct.pack('>I',binascii.crc32(kind+payload)&0xffffffff)
    png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(bytes(rows),6))+chunk(b'IEND',b'')
    return png,(width,height)

def show_desktop(value):
    x=C.CDLL(ctypes.util.find_library('X11'))
    x.XOpenDisplay.argtypes=[C.c_char_p];x.XOpenDisplay.restype=C.c_void_p
    x.XDefaultRootWindow.argtypes=[C.c_void_p];x.XDefaultRootWindow.restype=C.c_ulong
    x.XInternAtom.argtypes=[C.c_void_p,C.c_char_p,C.c_int];x.XInternAtom.restype=C.c_ulong
    class Data(C.Union):_fields_=[('b',C.c_char*20),('s',C.c_short*10),('l',C.c_long*5)]
    class Message(C.Structure):_fields_=[('type',C.c_int),('serial',C.c_ulong),('send',C.c_int),('display',C.c_void_p),('window',C.c_ulong),('message_type',C.c_ulong),('format',C.c_int),('data',Data)]
    class Event(C.Union):_fields_=[('message',Message),('pad',C.c_long*24)]
    x.XSendEvent.argtypes=[C.c_void_p,C.c_ulong,C.c_int,C.c_long,C.POINTER(Event)]
    x.XSync.argtypes=[C.c_void_p,C.c_int];x.XCloseDisplay.argtypes=[C.c_void_p]
    display=x.XOpenDisplay(os.environ['DISPLAY'].encode())
    if not display:raise RuntimeError('Cannot access the nested display')
    root=x.XDefaultRootWindow(display);event=Event();event.message.type=33;event.message.display=display;event.message.window=root;event.message.message_type=x.XInternAtom(display,b'_NET_SHOWING_DESKTOP',0);event.message.format=32;event.message.data.l[0]=value
    x.XSendEvent(display,root,0,(1<<20)|(1<<19),C.byref(event));x.XSync(display,0);x.XCloseDisplay(display)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    r=json.loads((Path.home()/'.local/state/xfce-wsl/session.json').read_text());os.environ.update(r['env'])
    def xfconf(*args):return subprocess.run(['xfconf-query','-c','xfce4-desktop',*args],text=True,capture_output=True)
    icon_property='/desktop-icons/style';old=xfconf('-p',icon_property)
    prop=subprocess.check_output(['xprop','-root','_NET_SHOWING_DESKTOP'],text=True)
    match=re.search(r'=\s*(\d+)',prop);was_showing=int(match.group(1)) if match else 0
    def interrupted(_signum,_frame):raise SystemExit('Capture interrupted; restoring UI')
    panel_settings=[]
    signal.signal(signal.SIGTERM,interrupted)
    try:
        # Task-button titles can reveal private documents or local application URLs.
        panel=subprocess.run(['xfconf-query','-c','xfce4-panel','-l'],text=True,capture_output=True)
        for key in panel.stdout.splitlines():
            if not re.fullmatch(r'/plugins/plugin-\d+',key):continue
            kind=subprocess.run(['xfconf-query','-c','xfce4-panel','-p',key],text=True,capture_output=True)
            if kind.stdout.strip()!='tasklist':continue
            prop=key+'/show-labels'
            original=subprocess.run(['xfconf-query','-c','xfce4-panel','-p',prop],text=True,capture_output=True)
            command=['xfconf-query','-c','xfce4-panel','-p',prop,'-s','false']
            if original.returncode!=0:command+=['--create','--type','bool']
            subprocess.run(command,check=True,capture_output=True)
            panel_settings.append((prop,original))
        command=['-p',icon_property,'-s','0']
        if old.returncode!=0:command+=['--create','--type','int']
        hidden=xfconf(*command)
        if hidden.returncode!=0:raise RuntimeError('Unable to hide desktop file labels')
        show_desktop(1);time.sleep(.8)
        prop=subprocess.check_output(['xprop','-root','_NET_SHOWING_DESKTOP'],text=True)
        if not re.search(r'=\s*1\b',prop):raise RuntimeError('Window manager did not hide applications; capture cancelled')
        raw=subprocess.check_output(['xwd','-root','-silent'])
        png,dimensions=xwd_to_png(raw)
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_bytes(png)
        print(json.dumps({'screenshot':str(args.output),'width':dimensions[0],'height':dimensions[1],'real_capture':True,'apps_hidden':True,'file_icons_hidden':True}))
    finally:
        for prop,original in reversed(panel_settings):
            command=['xfconf-query','-c','xfce4-panel','-p',prop]
            command+=['-s',original.stdout.strip()] if original.returncode==0 else ['--reset']
            subprocess.run(command,text=True,capture_output=True)
        if old.returncode==0:xfconf('-p',icon_property,'-s',old.stdout.strip())
        else:xfconf('-p',icon_property,'--reset')
        show_desktop(was_showing)
    return 0

if __name__=='__main__':raise SystemExit(main())
