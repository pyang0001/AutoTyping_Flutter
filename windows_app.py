"""Windows build entry. Opens the app window without the blocked runtime."""

import os
import traceback

os.environ["AUTOTYPER_EDGE"] = "1"

_LOG = os.path.join(os.environ.get("TEMP", "."), "autotyper-exe.log")


def _record(text: str) -> None:
    try:
        with open(_LOG, "a", encoding="utf-8") as handle:
            handle.write(text)
            if not text.endswith("\n"):
                handle.write("\n")
    except OSError:
        return


_record("start")

try:
    from app import main
except Exception:
    _record(traceback.format_exc())
    raise

if __name__ == "__main__":
    try:
        main()
    except Exception:
        _record(traceback.format_exc())
        raise
    _record("exit")
