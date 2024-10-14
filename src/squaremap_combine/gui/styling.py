"""
Handles building and applying themes and fonts to the GUI layout.
"""

from functools import cache

import dearpygui.dearpygui as dpg

from squaremap_combine.project import GUI_ASSETS


class Themes:
    """Builds `dearpygui` themes for GUI modules."""
    @cache # pylint: disable=method-cache-max-size-none; we deliberately want this class to only ever have one instance defined
    def __init__(self):
        with dpg.theme() as self.base:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 32, 32)
                dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (16, 16, 64, 255))

                dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255, 255))
                dpg.add_theme_color(dpg.mvThemeCol_TextDisabled, (255, 0, 0, 255))

                dpg.add_theme_style(dpg.mvStyleVar_TabRounding, 0, 0)
                dpg.add_theme_color(dpg.mvThemeCol_Tab, (64, 64, 96, 255))
                dpg.add_theme_color(dpg.mvThemeCol_TabHovered, (96, 96, 127, 255))
                dpg.add_theme_color(dpg.mvThemeCol_TabActive, (96, 96, 255, 255))

                dpg.add_theme_color(dpg.mvThemeCol_Button, (64, 64, 96, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (96, 96, 127, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (96, 96, 255, 255))

                dpg.add_theme_color(dpg.mvThemeCol_Separator, (127, 127, 255, 255))

            for comp in [dpg.mvInputText, dpg.mvInputIntMulti]:
                with dpg.theme_component(comp):
                    dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 4, 4)
                    dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 8, 4)
                    dpg.add_theme_style(dpg.mvStyleVar_ItemInnerSpacing, 8, 0)
                    dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (0, 0, 0, 255))

            for comp in [dpg.mvInputText, dpg.mvInputIntMulti]:
                with dpg.theme_component(comp, enabled_state=False):
                    dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 4, 4)
                    dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 8, 4)
                    dpg.add_theme_style(dpg.mvStyleVar_ItemInnerSpacing, 8, 0)
                    dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (127, 127, 127, 255))
                    dpg.add_theme_color(dpg.mvThemeCol_Text, (32, 32, 32, 255))

            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 4, 4)
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 16, 4)

            with dpg.theme_component(dpg.mvCheckbox):
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 4, 4)
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (0, 0, 0, 255))
                dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, (64, 64, 96, 255))
                dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, (96, 96, 127, 255))
                dpg.add_theme_color(dpg.mvThemeCol_CheckMark, (96, 96, 127, 255))

            with dpg.theme_component(dpg.mvProgressBar):
                dpg.add_theme_color(dpg.mvThemeCol_PlotHistogram, (0, 196, 0, 255))
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (32, 32, 32, 255))

        with dpg.theme() as self.tabs:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 16, 4)
                dpg.add_theme_style(dpg.mvStyleVar_ItemInnerSpacing, 0, 0)

        with dpg.theme() as self.console:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_ChildBg, (0, 0, 0, 255))
                dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 8, 8)
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 0, 0)

        with dpg.theme() as self.console_warning:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 0, 255))

        with dpg.theme() as self.console_error:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 0, 0, 255))

        with dpg.theme() as self.h1:
            with dpg.theme_component(dpg.mvText):
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 16, 16)

        with dpg.theme() as self.h2:
            with dpg.theme_component(dpg.mvText):
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 16, 16)

def apply_themes():
    """Binds themes to their respective items."""
    themes = Themes()
    dpg.bind_theme(themes.base)
    dpg.bind_item_font('title-text', themes.h1)
    dpg.bind_item_theme('console-output-window', themes.console)
    dpg.bind_item_theme('tabs-group', themes.tabs)

def configure_fonts():
    """Registers fonts and binds them to their respective items."""
    with dpg.font_registry():
        font_sans_regular = dpg.add_font(str(GUI_ASSETS / 'selawk.ttf'), 20)
        font_sans_regular_h1 = dpg.add_font(str(GUI_ASSETS / 'selawkb.ttf'), 30)
        font_sans_regular_h2 = dpg.add_font(str(GUI_ASSETS / 'selawkb.ttf'), 40)
        font_mono = dpg.add_font(str(GUI_ASSETS / 'SourceCodePro-SemiBold.ttf'), 20)

    dpg.bind_font(font_sans_regular)
    dpg.bind_item_font('title-text', font_sans_regular_h1)
    dpg.bind_item_font('console-output-window', font_mono)
