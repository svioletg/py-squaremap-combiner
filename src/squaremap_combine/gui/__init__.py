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

A `logger` handler is added in `combine_gui` which is used to send logs to a "console window" that appears
at the bottom of the GUI app. It is set up to only append logs to this list when the console window's `user_data` is set to
`{'allow-output': True}`, and its level is set to `GUI_COMMAND`, which is a special logging level exclusively used
to communicate actions to GUI modules when other means either aren't possible or would significantly clutter
pre-existing code. For example, logs of this level are used in `squaremap_combine.combine_core` to update the
progress bar at the bottom of the window of the GUI with minimal changes to the `Combiner.combine()` method's actual code.

At present only one "command" is recognized, that being `/pbar` (syntax: `/pbar hide`, `/pbar set <value>`),
used to update the progress bar as previously mentioned. GUI command logs are parsed by simply splitting the string by spaces,
and the overall process is very rudimentary. Additional documentation on this system will be added in future if it sees
more use outside of `/pbar`.
"""
