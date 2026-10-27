"""Portable configuration contract; standard-library tests, no display required."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
LIB=ROOT/'linux/lib/common.py'

class ConfigurationTests(unittest.TestCase):
 def module(self):
  if not LIB.exists():self.fail('Portable configuration module has not been implemented')
  spec=importlib.util.spec_from_file_location('xfce_common',LIB)
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  return module
 def test_defaults_are_windowed_and_target_144(self):
  m=self.module();cfg=m.load_config(ROOT/'tests/absent-config.json')
  self.assertTrue(cfg['windowed']);self.assertEqual(cfg['refresh_rate'],144)
  self.assertEqual(cfg['adapter'],'auto');self.assertEqual(cfg['window_title'],'Xfce WSL')
 def test_native_paths_with_spaces_are_separate_arguments(self):
  m=self.module();cfg=m.load_config(ROOT/'tests/absent-config.json')
  cfg.update(windows_helper_dir=r'C:\Users\Example Person\AppData\Local\XfceWSLToolkit',powershell_wsl='/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe')
  command=m.windows_command('clipboard-host.ps1',cfg)
  self.assertEqual(command[-2],'-File');self.assertEqual(command[-1],r'C:\Users\Example Person\AppData\Local\XfceWSLToolkit\clipboard-host.ps1')
  self.assertIn('-STA',command)
 def test_helper_path_traversal_is_rejected(self):
  m=self.module();cfg=m.load_config(ROOT/'tests/absent-config.json')
  cfg['windows_helper_dir']=r'C:\Tools'
  with self.assertRaises(ValueError):m.windows_command('../unexpected.ps1',cfg)
 def test_invalid_refresh_is_rejected(self):
  m=self.module()
  base=ROOT/'.test-output';base.mkdir(exist_ok=True)
  with tempfile.TemporaryDirectory(dir=base) as d:
   p=Path(d)/'settings.json'
   for value in (0,145,True,'invalid'):
    p.write_text(json.dumps({'refresh_rate':value}))
    with self.subTest(value=value):
     with self.assertRaises(ValueError):m.load_config(p)
 def test_invalid_json_fails_closed(self):
  m=self.module();base=ROOT/'.test-output';base.mkdir(exist_ok=True)
  with tempfile.TemporaryDirectory(dir=base) as d:
   p=Path(d)/'settings.json';p.write_text('{not JSON')
   with self.assertRaises(ValueError):m.load_config(p)
 def test_direct_rendering_does_not_mean_hardware(self):
  m=self.module();info=m.renderer_info('direct rendering: Yes\n Accelerated: no\nOpenGL renderer string: llvmpipe (LLVM)\n')
  self.assertFalse(info['accelerated'])
 def test_d3d12_renderer_is_detected(self):
  m=self.module();info=m.renderer_info(' Accelerated: yes\nOpenGL renderer string: D3D12 (Example GPU)\n')
  self.assertTrue(info['accelerated']);self.assertEqual(info['renderer'],'D3D12 (Example GPU)')
 def test_monitor_order_is_spatial_not_output_name(self):
  m=self.module();monitors=[dict(name='rdp-0',x=2560,y=0,width=1920,height=1080),dict(name='rdp-9',x=0,y=0,width=2560,height=1080)]
  self.assertEqual(m.select_monitor(monitors,'left')['name'],'rdp-9')
  self.assertEqual(m.select_monitor(monitors,'right')['name'],'rdp-0')
 def test_window_rect_clamps_to_a_smaller_monitor(self):
  m=self.module()
  if not hasattr(m,'window_rect'):self.fail('Windowed monitor placement has not been implemented')
  rect=m.window_rect({'WIDTH':2560,'HEIGHT':1440},{'x':1920,'y':0,'width':1920,'height':1080})
  self.assertLess(rect['WIDTH'],1920);self.assertLess(rect['HEIGHT'],1080)
  self.assertGreaterEqual(rect['X'],1920);self.assertGreaterEqual(rect['Y'],0)
 def test_empty_monitor_list_is_rejected(self):
  with self.assertRaises(ValueError):self.module().select_monitor([],'left')

if __name__=='__main__':unittest.main()
