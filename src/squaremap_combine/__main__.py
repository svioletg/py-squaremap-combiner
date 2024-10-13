import sys

from . import combine_cli

if __name__ == '__main__':
    if 'gui' in sys.argv[1:]:
        from squaremap_combine.gui import combine_gui
        sys.exit(combine_gui.main())
    else:
        sys.exit(combine_cli.main())
