"""Offline packaging tests only."""
import importlib.util
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("salusfy_checks",ROOT/"tools/check_repository.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class TestPackaging(unittest.TestCase):
    def test_repository(self):
        self.assertEqual(mod.validate(ROOT),[])
    def test_manifest_domain(self):
        import json
        manifest=json.loads((ROOT/"custom_components/salus/manifest.json").read_text())
        self.assertEqual(manifest["domain"],"salus")
        self.assertEqual(manifest["version"],"1.2.0")
if __name__=="__main__":unittest.main()
