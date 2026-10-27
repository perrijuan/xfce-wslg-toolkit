"""Installation is staged in a disposable HOME; never changes the live profile."""
import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
INSTALLER=ROOT/'tools/install.py'

class InstallerTests(unittest.TestCase):
 def run_installer(self,*args,home):
  if not INSTALLER.exists():self.fail('Portable installer has not been implemented')
  env=dict(os.environ,HOME=str(home),XDG_CONFIG_HOME=str(home/'.config'))
  return subprocess.run([sys.executable,str(INSTALLER),*map(str,args)],env=env,text=True,capture_output=True)
 def workdir(self):
  base=ROOT/'.test-output';base.mkdir(exist_ok=True)
  return tempfile.TemporaryDirectory(dir=base)
 def test_dry_run_has_no_filesystem_side_effects(self):
  with self.workdir() as d:
   home=Path(d)/'new user home';prefix=home/'toolkit with spaces'
   result=self.run_installer('--dry-run','--prefix',prefix,home=home)
   self.assertEqual(result.returncode,0,result.stderr)
   plan=json.loads(result.stdout);self.assertTrue(plan['dry_run'])
   self.assertFalse(home.exists());self.assertIn('xserver-xephyr',plan['packages'])
 def test_invalid_refresh_changes_nothing(self):
  with self.workdir() as d:
   home=Path(d)/'untouched'
   result=self.run_installer('--dry-run','--refresh-rate','0',home=home)
   self.assertNotEqual(result.returncode,0);self.assertFalse(home.exists())
 @unittest.skipUnless(sys.platform.startswith('linux'),'Linux user-local staging test')
 def test_staged_install_is_idempotent_and_keeps_aliases(self):
  with self.workdir() as d:
   home=Path(d)/'profile with spaces';home.mkdir()
   aliases=home/'.bash_aliases';aliases.write_text("alias keepme='printf preserved'\n")
   args=('--skip-packages','--skip-windows','--prefix',home/'runtime with spaces')
   for _ in range(2):
    result=self.run_installer(*args,home=home)
    self.assertEqual(result.returncode,0,result.stdout+result.stderr)
   text=aliases.read_text();self.assertIn('alias keepme=',text)
   self.assertEqual(text.count('# BEGIN XFCE WSLG TOOLKIT'),1)
   self.assertEqual(text.count('alias xfce='),1)
   config=json.loads((home/'.config/xfce-wsl/config.json').read_text())
   self.assertTrue(config['windowed']);self.assertEqual(config['refresh_rate'],144)
   command=home/'.local/bin/xfce-wsl';self.assertTrue(command.exists())
   check=subprocess.run(['bash','-n',str(command)],capture_output=True,text=True)
   self.assertEqual(check.returncode,0,check.stderr)
   self.assertFalse((home/'.config/autostart/xfce-wsl-clipboard.desktop').exists())
 def test_runtime_has_no_reference_machine_paths(self):
  forbidden=('/home/'+'astra','C:\\Users\\'+'perri','/usr/local/lib/'+'xfce-wsl')
  for folder in ('linux','windows','config'):
   for p in (ROOT/folder).rglob('*'):
    if p.is_file() and '__pycache__' not in p.parts:
     text=p.read_text(encoding='utf-8')
     for value in forbidden:
      with self.subTest(file=p.name,value=value):self.assertNotIn(value,text)
 def test_python_runtime_parses_without_display(self):
  for p in (ROOT/'linux/lib').glob('*.py'):
   with self.subTest(file=p.name):ast.parse(p.read_text(encoding='utf-8'),filename=str(p))

if __name__=='__main__':unittest.main()
