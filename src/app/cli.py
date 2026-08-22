"""
cli.py — Fokiz CLI entry point. Parses arguments and delegates to commands.py.
Copyright (C) Alenia Studios — GNU GPL v3

RULES:
- No business logic here.
- No SQL.
- No math.
- Pure argument parsing and delegation.
"""

import sys
import logging
from .errors import FokizError, NotInitializedError
from . import ui
from .i18n import _


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )


def _usage() -> None:
    print(_("cli_usage"))


def main() -> int:
    _setup_logging()

    args = sys.argv[1:]

    if not args or args[0] in ("help", "--help", "-h"):
        _usage()
        return 0

    cmd = args[0]

    try:
        if cmd == "init":
            from .commands import cmd_init
            return cmd_init()

        elif cmd == "add":
            from .commands import cmd_add
            return cmd_add()

        elif cmd == "status":
            show_banner = "--banner" in args
            show_completed = "--complete" in args or "--completed" in args
            from .commands import cmd_status
            return cmd_status(show_banner=show_banner, show_completed=show_completed)

        elif cmd == "board":
            from .commands import cmd_board
            return cmd_board()

        elif cmd == "done":
            if len(args) < 2:
                ui.print_error(_("cli_usage_done"))
                return 1
            try:
                task_id = int(args[1])
            except ValueError:
                ui.print_error(_("cli_invalid_task_id", task_id=args[1]))
                return 1
            from .commands import cmd_done
            return cmd_done(task_id)

        elif cmd == "surrender":
            if len(args) < 2:
                ui.print_error(_("cli_usage_surrender"))
                return 1
            try:
                task_id = int(args[1])
            except ValueError:
                ui.print_error(_("cli_invalid_task_id", task_id=args[1]))
                return 1
            from .commands import cmd_surrender
            return cmd_surrender(task_id)

        else:
            ui.print_error(_("cli_unknown_cmd", cmd=cmd))
            _usage()
            return 1

    except NotInitializedError as e:
        ui.print_error(str(e))
        return 1
    except FokizError as e:
        ui.print_error(str(e))
        return 1
    except KeyboardInterrupt:
        print()
        ui.print_info(_("cli_cancelled"))
        return 130


if __name__ == "__main__":
    sys.exit(main())
