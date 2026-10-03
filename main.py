"""
CloakPix Launcher Script.
Run 'python main.py' to launch the GUI.
Run 'python main.py --help' for CLI options.
"""

import sys

if __name__ == "__main__":
    if len(sys.argv) > 1:
        from cloakpix.cli import main
        main()
    else:
        from cloakpix.app import run_app
        run_app()

