$ErrorActionPreference='Stop'
[Console]::InputEncoding=New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding=New-Object System.Text.UTF8Encoding($false)
Add-Type -ReferencedAssemblies System.Windows.Forms,System.Web.Extensions -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.Collections.Concurrent;
using System.Runtime.InteropServices;
using System.Threading;
using System.Web.Script.Serialization;
using System.Windows.Forms;
public static class XfceNativeClipboard {
 [DllImport("user32.dll")] static extern uint GetClipboardSequenceNumber();
 static JavaScriptSerializer json=new JavaScriptSerializer { MaxJsonLength=16777216 };
 static ConcurrentQueue<string> incoming=new ConcurrentQueue<string>();
 static volatile bool done=false;
 static long sent=-1;
 static void Emit(object value) { Console.Out.WriteLine(json.Serialize(value)); Console.Out.Flush(); }
 static void Snapshot() {
  uint before=GetClipboardSequenceNumber();
  bool available=Clipboard.ContainsText(TextDataFormat.UnicodeText);
  string text=available?Clipboard.GetText(TextDataFormat.UnicodeText):null;
  uint after=GetClipboardSequenceNumber();
  if (before!=after) return;
  Emit(new {kind="clipboard",seq=after,text=text}); sent=after;
 }
 public static void Run() {
  var reader=new Thread(()=>{try {string line;while((line=Console.In.ReadLine())!=null) incoming.Enqueue(line);}finally {done=true;}});
  reader.IsBackground=true;reader.Start();
  while(!done) {
   try {
    string line;
    while(incoming.TryDequeue(out line)) {
     var item=json.Deserialize<Dictionary<string,object>>(line);
     if(!item.ContainsKey("kind") || (string)item["kind"]!="set") continue;
     uint expected=Convert.ToUInt32(item["seq"]);
     if(GetClipboardSequenceNumber()!=expected) {Snapshot();continue;}
     string text=(string)item["text"];
     if(text==null || text.Length>8388608) continue;
     bool same=Clipboard.ContainsText(TextDataFormat.UnicodeText) && Clipboard.GetText(TextDataFormat.UnicodeText)==text;
     if(!same) {
      var data=new DataObject();data.SetData(DataFormats.UnicodeText,true,text);
      Clipboard.SetDataObject(data,true,5,50);
     }
     uint seq=GetClipboardSequenceNumber();sent=seq;
     Emit(new {kind="ack",seq=seq});
    }
    if((long)GetClipboardSequenceNumber()!=sent) Snapshot();
   } catch(System.Runtime.InteropServices.ExternalException) {
    // Another application temporarily owns the clipboard lock; retry shortly.
   } catch(Exception error) {
    Console.Error.WriteLine("Native clipboard helper: "+error.GetType().Name);
   }
   Thread.Sleep(150);
  }
 }
}
'@
[XfceNativeClipboard]::Run()
