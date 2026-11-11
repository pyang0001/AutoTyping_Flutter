"""Open Auto Typer in the browser."""

import sys

from app import main

if __name__ == "__main__":
    if "--web" not in sys.argv:
        sys.argv.append("--web")
    main()
