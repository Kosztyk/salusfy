"""Regression tests for HACS domain-collision and migration changes."""
import json
from pathlib import Path
import unittest
from support import ROOT, load

class TestDomainRename(unittest.TestCase):
    def test_manifest_const_and_folder_agree(self):
        pkg = ROOT / "custom_components/salus_cloud_native"
        manifest = json.loads((pkg / "manifest.json").read_text())
        const = load("const")
        self.assertEqual(const.DOMAIN, manifest["domain"])
        self.assertEqual(const.DOMAIN, pkg.name)
        self.assertTrue(const.DOMAIN.isidentifier())
        self.assertFalse((ROOT / "custom_components/salus").exists())

    def test_device_id_namespace_and_stable_cloud_id(self):
        from types import SimpleNamespace
        device = load("device")
        info = device.salus_device_info(SimpleNamespace(device_id="STA123", device=SimpleNamespace(name="Living Room")))
        self.assertEqual(info["identifiers"], {("salus_cloud_native", "STA123")})

    def test_migration_steps_documented(self):
        readme = (ROOT / "README.md").read_text()
        for important in ("old Salusfy config entry", "not automatically converted", "entity IDs", "homeassistant_salus"):
            self.assertIn(important, readme)

if __name__ == "__main__":
    unittest.main()
