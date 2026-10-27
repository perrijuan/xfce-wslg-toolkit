import importlib.util
from pathlib import Path
import struct
import unittest
import zlib

ROOT=Path(__file__).resolve().parents[1]

class ScreenshotTests(unittest.TestCase):
 def module(self):
  path=ROOT/'tools/screenshot.py'
  if not path.exists():self.fail('Portable screenshot decoder has not been implemented')
  spec=importlib.util.spec_from_file_location('screenshot',path)
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
 def test_xwd_24bit_stride_produces_real_rgb_png(self):
  header=[100,7,2,24,2,1,0,0,32,0,32,24,8,4,0xff0000,0xff00,0xff,8,256,0,2,1,0,0,0]
  raw=struct.pack('>25I',*header)+bytes([0,0,255,0,255,0,0,0])
  png,dimensions=self.module().xwd_to_png(raw)
  self.assertEqual(dimensions,(2,1));self.assertEqual(png[:8],b'\x89PNG\r\n\x1a\n')
  offset=8;payload=b''
  while offset<len(png):
   length=struct.unpack('>I',png[offset:offset+4])[0];kind=png[offset+4:offset+8]
   if kind==b'IDAT':payload+=png[offset+8:offset+8+length]
   offset+=length+12
  self.assertEqual(zlib.decompress(payload),bytes([0,255,0,0,0,255,0]))
 def test_truncated_image_is_rejected(self):
  with self.assertRaises(ValueError):self.module().xwd_to_png(b'not an image')

if __name__=='__main__':unittest.main()
