"""Windows build entry. Opens the app window without the blocked runtime."""

import os

os.environ["AUTOTYPER_EDGE"] = "1"

from app import main

if __name__ == "__main__":
    main()
