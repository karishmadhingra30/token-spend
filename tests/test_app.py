import sys

import app


def test_refresh_pricing_modules_handles_missing_sys_modules_entry():
    original_pricing = sys.modules.pop("pricing", None)
    try:
        assert app.refresh_pricing_modules() is True
        assert "pricing" in sys.modules
    finally:
        if original_pricing is not None:
            sys.modules["pricing"] = original_pricing
