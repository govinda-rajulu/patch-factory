import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("pagegen", ROOT / "src/etc/pagegen.py")
pagegen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pagegen)


class Pagegen(unittest.TestCase):
    def test_label_cannot_close_inline_script(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json") as f:
            json.dump([{"id": "safe", "enabled": True, "label": "</script><script>alert(1)</script>"}], f)
            f.flush()
            generated = pagegen.build(f.name)
        self.assertNotIn("</script>", generated)
        self.assertIn(r"\u003c/script\u003e", generated)


if __name__ == "__main__":
    unittest.main()
