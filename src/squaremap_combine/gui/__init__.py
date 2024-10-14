"""
The `gui` submodule provides a basic GUI application for interacting with `squaremap_combine`'s functionality.
The requirements for the GUI portion of this project are not installed by default; install the package with
`[gui]` appended to the package name in order to install them:

```bash
pip install squaremap_combine[gui]
```

Once the requirements are installed, you can open the GUI app by running the module with the `gui` argument:

```bash
python3 -m squaremap_combine gui
```

Add `debug` to the end of the command to enable debug logs & the debug tab.

This submodule is split up into further submodules to contain each aspect of the GUI creation / handling process.
You can think of `layout` as the HTML, `styling` as the CSS, and `actions` as the scripting, in a way.
`combine_gui` houses the main entrypoint to actually launch the GUI app.
"""
