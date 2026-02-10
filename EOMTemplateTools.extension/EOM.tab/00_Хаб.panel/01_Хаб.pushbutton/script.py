"""LEGACY ENTRYPOINT (disabled).

This button was a legacy launcher for a local HTML dashboard.
The project now uses the UniTools/EOM Hub from:
  EOM.tab/01_Хаб.panel/Hub.pushbutton

We intentionally block execution here to keep a single source of truth.
"""

try:
    from pyrevit import forms
    forms.alert(
        "Этот пункт меню устарел и отключён. Используйте: EOM → Hub (в панели 01_Хаб).",
        title="EOM Hub",
        warn_icon=True,
    )
except Exception:
    pass

raise SystemExit
