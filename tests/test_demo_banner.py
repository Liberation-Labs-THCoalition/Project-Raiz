"""--demo must say, in the output, that the data is invented (not only in the README)."""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(*args):
    return subprocess.run([sys.executable, "-m", "raiz", *args], cwd=ROOT, capture_output=True,
                          text=True, encoding="utf-8", env=dict(os.environ, PYTHONIOENCODING="utf-8"))


def test_demo_says_the_data_is_invented_before_and_after_and_names_the_zip():
    out = run("query", "99999", "--demo", "--actions").stdout
    assert out.count("DEMO: INVENTED DATA") == 2
    assert "not about 99999" in out and "Nothing here describes 99999" in out
    assert out.index("INVENTED DATA") < out.index("Environmental Report")
    assert out.rindex("INVENTED DATA") > out.index("SUGGESTED ACTIONS")
    assert "Querying EPA ECHO" not in out          # nothing was queried


def test_demo_facilities_do_not_depend_on_the_zip():
    """Which is why the banner says the examples are fixed whatever zip code you give."""
    def facilities(zip_code):
        out = run("query", zip_code, "--demo").stdout
        return out[out.index("REGULATED FACILITIES"):out.index("Community Demographics")].replace(zip_code, "ZIP")
    assert facilities("62701") == facilities("99999") and "Springfield Chemical Corp" in facilities("99999")
