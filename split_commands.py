import re
from pathlib import Path

content = Path("src/app/commands.py").read_text()

def extract_section(start_marker, end_marker=None):
    if end_marker:
        pattern = f"({start_marker}.*?)(?={end_marker})"
    else:
        pattern = f"({start_marker}.*)"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        return match.group(1)
    return ""

header = extract_section(".*?", "# ---------------------------------------------------------------------------")

init_code = header + extract_section("# ---------------------------------------------------------------------------\n# SYSTEMD UNIT TEMPLATES", "# ---------------------------------------------------------------------------\n# cmd_add")
add_code = header + extract_section("# ---------------------------------------------------------------------------\n# cmd_add", "def cmd_status")
status_code = header + extract_section("def cmd_status", "# ---------------------------------------------------------------------------\n# cmd_done")
done_code = header + extract_section("# ---------------------------------------------------------------------------\n# cmd_done", "# ---------------------------------------------------------------------------\n# cmd_surrender")
surrender_code = header + extract_section("# ---------------------------------------------------------------------------\n# cmd_surrender", "# ---------------------------------------------------------------------------\n# cmd_board")
guard_code = extract_section("# ---------------------------------------------------------------------------\n# Guard", "# ---------------------------------------------------------------------------\n# cmd_board")
surrender_code += guard_code
board_code = header + guard_code + extract_section("# ---------------------------------------------------------------------------\n# cmd_board", "# ---------------------------------------------------------------------------\n# cmd_lang")
lang_code = header + guard_code + extract_section("# ---------------------------------------------------------------------------\n# cmd_lang")

Path("src/app/commands/__init__.py").write_text("")
Path("src/app/commands/init.py").write_text(init_code)
Path("src/app/commands/add.py").write_text(add_code)
Path("src/app/commands/status.py").write_text(status_code)
Path("src/app/commands/done.py").write_text(done_code)
Path("src/app/commands/surrender.py").write_text(surrender_code)
Path("src/app/commands/board.py").write_text(board_code)
Path("src/app/commands/lang.py").write_text(lang_code)

print("Split complete")
