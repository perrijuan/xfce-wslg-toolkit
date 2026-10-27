import importlib.util
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class PrivacyScannerTests(unittest.TestCase):
 def scanner(self):
  p=ROOT/'tools/check_repository.py'
  if not p.exists():self.fail('Repository privacy scanner has not been implemented')
  spec=importlib.util.spec_from_file_location('scanner',p);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
 def test_token_like_literal_is_reported(self):
  self.assertTrue(self.scanner().scan_text('demo.txt','token='+('sk-'+'A'*32)))
 def test_placeholder_is_not_a_credential(self):
  self.assertFalse(self.scanner().scan_text('demo.txt','TOKEN=<YOUR_TOKEN>'))
if __name__=='__main__':unittest.main()
