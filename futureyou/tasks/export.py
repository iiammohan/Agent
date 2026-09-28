"""Leave any time: zip everything, or delete everything."""

from __future__ import annotations

import shutil
import zipfile
from datetime import date
from pathlib import Path


def export(store, out_dir: Path | None = None, say=print) -> Path:
    out_dir = Path(out_dir or ".").resolve()
    target = out_dir / f"futureyou-export-{date.today().strftime('%Y%m%d')}.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(store.home.rglob("*")):
            if p.is_file() and not p.name.startswith(".tmp-"):
                z.write(p, p.relative_to(store.home))
    say(f"Exported to {target}")
    return target


def delete_all(store, ask=input, say=print) -> bool:
    if not store.exists():
        say("Nothing to delete.")
        return False
    say(f"This deletes everything under {store.home}. There is no undo.")
    if ask("Type 'delete' to confirm: ").strip() != "delete":
        say("Kept.")
        return False
    shutil.rmtree(store.home)
    say("Deleted.")
    return True
