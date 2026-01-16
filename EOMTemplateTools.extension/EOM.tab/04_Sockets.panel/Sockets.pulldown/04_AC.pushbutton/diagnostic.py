# -*- coding: utf-8 -*-
"""
Diagnostic script for AC Socket Placement
Checks all dependencies and configurations
"""
import sys
import os

# Add lib path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))))

from pyrevit import script

def test_imports():
    """Test all required imports"""
    output = script.get_output()
    output.print_md("## Testing Imports")

    tests = []

    # Test 1: pyrevit modules
    try:
        from pyrevit import DB, forms, revit
        tests.append(("✅", "pyrevit modules", "OK"))
    except Exception as e:
        tests.append(("❌", "pyrevit modules", str(e)))

    # Test 2: lib modules
    try:
        import config_loader
        tests.append(("✅", "config_loader", "OK"))
    except Exception as e:
        tests.append(("❌", "config_loader", str(e)))

    try:
        import link_reader
        tests.append(("✅", "link_reader", "OK"))
    except Exception as e:
        tests.append(("❌", "link_reader", str(e)))

    try:
        import socket_utils
        tests.append(("✅", "socket_utils", "OK"))
    except Exception as e:
        tests.append(("❌", "socket_utils", str(e)))

    try:
        import utils_revit
        tests.append(("✅", "utils_revit", "OK"))
    except Exception as e:
        tests.append(("❌", "utils_revit", str(e)))

    try:
        import utils_units
        tests.append(("✅", "utils_units", "OK"))
    except Exception as e:
        tests.append(("❌", "utils_units", str(e)))

    # Print results
    for icon, name, result in tests:
        output.print_md(u"{0} **{1}**: {2}".format(icon, name, result))

    return all(t[0] == "✅" for t in tests)

def test_config():
    """Test configuration loading"""
    output = script.get_output()
    output.print_md("\n## Testing Configuration")

    try:
        import config_loader
        rules = config_loader.load_rules()

        if rules:
            output.print_md("✅ **Config loaded successfully**")

            # Check critical AC params
            critical_params = [
                'socket_ac_height_from_ceiling_mm',
                'socket_ac_offset_from_corner_mm',
                'ac_socket_avoid_external_wall',
                'ac_basket_family_keywords'
            ]

            for param in critical_params:
                if param in rules:
                    output.print_md(u"  ✅ `{0}`: {1}".format(param, rules[param]))
                else:
                    output.print_md(u"  ❌ **Missing param**: `{0}`".format(param))

            return True
        else:
            output.print_md("❌ **Failed to load config**")
            return False

    except Exception as e:
        output.print_md(u"❌ **Config error**: {0}".format(e))
        import traceback
        output.print_code(traceback.format_exc())
        return False

def test_document():
    """Test Revit document access"""
    output = script.get_output()
    output.print_md("\n## Testing Revit Document")

    try:
        from pyrevit import revit
        doc = revit.doc

        if doc:
            output.print_md(u"✅ **Document**: {0}".format(doc.Title))
            output.print_md(u"  **Path**: {0}".format(doc.PathName or 'Not saved'))
            return True
        else:
            output.print_md("❌ **No active document**")
            return False

    except Exception as e:
        output.print_md(u"❌ **Document error**: {0}".format(e))
        return False

def test_links():
    """Test architectural link detection"""
    output = script.get_output()
    output.print_md("\n## Testing AR Links")

    try:
        from pyrevit import revit
        import link_reader

        doc = revit.doc
        if not doc:
            output.print_md("❌ **No active document**")
            return False

        links = link_reader.list_link_instances(doc)

        if links:
            output.print_md(u"✅ **Found {0} link(s)**:".format(len(links)))
            for ln in links[:5]:  # Show first 5
                try:
                    name = ln.Name
                    loaded = link_reader.is_link_loaded(ln)
                    status = "🟢 Loaded" if loaded else "🔴 Not loaded"
                    output.print_md(u"  - **{0}** {1}".format(name, status))
                except:
                    pass
            return True
        else:
            output.print_md("⚠️ **No links found** (this is OK if testing without AR model)")
            return True

    except Exception as e:
        output.print_md(u"❌ **Link error**: {0}".format(e))
        import traceback
        output.print_code(traceback.format_exc())
        return False

def test_socket_symbol():
    """Test socket symbol detection"""
    output = script.get_output()
    output.print_md("\n## Testing Socket Symbols")

    try:
        from pyrevit import revit, DB
        import socket_utils

        doc = revit.doc
        if not doc:
            output.print_md("❌ **No active document**")
            return False

        # List available socket types
        socket_types = socket_utils._list_loaded_socket_type_labels(doc, limit=20)

        if socket_types:
            output.print_md(u"✅ **Found {0} socket type(s)**:".format(len(socket_types)))
            for st in socket_types[:10]:  # Show first 10
                output.print_md(u"  - `{0}`".format(st))
            return True
        else:
            output.print_md("⚠️ **No socket families found**")
            output.print_md("  💡 **Tip**: Load socket families (TSL_EF_...) into the project")
            return False

    except Exception as e:
        output.print_md(u"❌ **Symbol error**: {0}".format(e))
        import traceback
        output.print_code(traceback.format_exc())
        return False

def main():
    output = script.get_output()
    output.print_md("# 🔍 AC Socket Placement - Diagnostic Report")
    output.print_md("---")

    results = []
    results.append(("Imports", test_imports()))
    results.append(("Configuration", test_config()))
    results.append(("Document", test_document()))
    results.append(("AR Links", test_links()))
    results.append(("Socket Symbols", test_socket_symbol()))

    output.print_md("\n---")
    output.print_md("## 📊 Summary")

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        icon = "✅" if result else "❌"
        output.print_md(f"{icon} **{name}**")

    output.print_md(u"\n**Result**: {0}/{1} tests passed".format(passed, total))

    if passed == total:
        output.print_md("\n🎉 **All tests passed!** Script should work.")
    else:
        output.print_md("\n⚠️ **Some tests failed.** Fix issues above before running main script.")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        output = script.get_output()
        output.print_md("# ❌ Critical Error")
        output.print_md(u"**{0}**".format(str(e)))
        import traceback
        output.print_code(traceback.format_exc())
