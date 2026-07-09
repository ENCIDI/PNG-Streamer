import flet as ft

PANEL_BGCOLOR = ft.Colors.with_opacity(0.55, "#160F22")


def panel(content: ft.Control) -> ft.Container:
    return ft.Container(
        margin=16,
        padding=24,
        border_radius=20,
        bgcolor=PANEL_BGCOLOR,
        content=content,
    )
