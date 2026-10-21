import json
from pathlib import Path
import subprocess
import sys
import unicodedata


def test_platform_imports_and_pm25_unit_do_not_use_deprecated_constants():
    # A fresh interpreter observes warnings even when another test imported sensors.
    script = '''
import importlib
import json
from custom_components.gac_connect.const import PLATFORMS
for platform in PLATFORMS:
    importlib.import_module(f"custom_components.gac_connect.{platform}")
from custom_components.gac_connect.sensor import SENSORS
print(json.dumps(next(s.native_unit_of_measurement for s in SENSORS if s.key == "pm25")))
'''
    result = subprocess.run([sys.executable, "-c", script], cwd=Path(__file__).resolve().parents[1],
                            capture_output=True, text=True, timeout=30, check=False)
    assert result.returncode == 0, result.stderr
    # Older HA used the micro sign; the enum uses Greek mu for the same unit.
    assert unicodedata.normalize("NFKC", json.loads(result.stdout)) == "μg/m3"
    assert "CONCENTRATION_MICROGRAMS_PER_CUBIC_METER" not in result.stderr
