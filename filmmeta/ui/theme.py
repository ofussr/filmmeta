"""Explicit light and dark Fusion palettes, independent of the OS theme."""

from PySide6.QtGui import QColor, QPalette
from importlib.resources import files


def apply_theme(app, theme="light"):
    app.setStyle("Fusion")
    palette = QPalette()
    dark = theme == "dark"
    colors = {
        "Window": "#252930" if dark else "#f5f6f7",
        "Base": "#1c2026" if dark else "#ffffff",
        "AlternateBase": "#303640" if dark else "#edf0f3",
        "Button": "#353c47" if dark else "#e9edf1",
        "WindowText": "#edf1f7" if dark else "#20252b",
        "Text": "#edf1f7" if dark else "#20252b",
        "ButtonText": "#edf1f7" if dark else "#20252b",
        "PlaceholderText": "#9ba8ba" if dark else "#707984",
        "ToolTipBase": "#353c47" if dark else "#ffffff",
        "ToolTipText": "#edf1f7" if dark else "#20252b",
        "Highlight": "#447bbd" if dark else "#316baf",
        "HighlightedText": "#ffffff",
        "Link": "#88baff" if dark else "#316baf",
    }
    for role, color in colors.items():
        palette.setColor(getattr(QPalette.ColorRole, role), QColor(color))
    for role in ("WindowText", "Text", "ButtonText"):
        palette.setColor(
            QPalette.ColorGroup.Disabled,
            getattr(QPalette.ColorRole, role),
            QColor("#8591a0" if dark else "#7c8590"),
        )
    app.setPalette(palette)
    if dark:
        check = files("filmmeta.resources").joinpath("check.svg").as_posix()
        partial = files("filmmeta.resources").joinpath("partial-check.svg").as_posix()
        app.setStyleSheet(f'''
            QCheckBox::indicator, QTreeView::indicator {{
                width: 14px; height: 14px; border: 1px solid #8293a8;
                border-radius: 2px; background: #1c2026;
            }}
            QCheckBox::indicator:checked, QTreeView::indicator:checked {{
                background: #447bbd; border-color: #88baff; image: url("{check}");
            }}
            QCheckBox::indicator:indeterminate, QTreeView::indicator:indeterminate {{
                background: #526273; image: url("{partial}");
            }}
            QCheckBox::indicator:disabled, QTreeView::indicator:disabled {{
                border-color: #596575;
            }}
        ''')
    else:
        app.setStyleSheet("")


def apply_light_theme(app):
    apply_theme(app, "light")
