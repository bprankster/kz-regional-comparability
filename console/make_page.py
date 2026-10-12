"""Embed console/data.json into console/console.html → console/StatQUO_console.html (one self-contained page)."""
from pathlib import Path
here = Path(__file__).parent
data = (here / "data.json").read_text(encoding="utf-8").replace("</", "<\\/")
page = (here / "console.html").read_text(encoding="utf-8").replace("/*DATA*/null", data)
(here / "StatQUO_console.html").write_text(page, encoding="utf-8")
print("written", len(page))
