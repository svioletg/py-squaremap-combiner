"""
Theme constants for GUI modules.
"""

from functools import cache

import dearpygui.dearpygui as dpg


class Themes:
    """Builds `dearpygui` themes for GUI modules."""
    @cache # pylint: disable=method-cache-max-size-none; we deliberately want this class to only ever have one instance defined
    def __init__(self):
        with dpg.theme() as self.base:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (32, 32, 32, 255), category=dpg.mvThemeCat_Core)
                dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 32, 32, category=dpg.mvThemeCat_Core)

            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 16, 8, category=dpg.mvThemeCat_Core)

        with dpg.theme() as self.console:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_ChildBg, (0, 0, 0, 255), category=dpg.mvThemeCat_Core)
                dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 8, 8, category=dpg.mvThemeCat_Core)
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 0, 0, category=dpg.mvThemeCat_Core)

        with dpg.theme() as self.console_warning:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 0, 255), category=dpg.mvThemeCat_Core)

        with dpg.theme() as self.console_error:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 0, 0, 255), category=dpg.mvThemeCat_Core)
