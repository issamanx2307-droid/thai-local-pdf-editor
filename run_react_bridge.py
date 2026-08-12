# -*- coding: utf-8 -*-
"""Entrypoint for the local React PDF bridge sidecar.

The packaged sidecar also acts as the isolated GDI print worker.  This is
important because the Tauri installation does not contain ``run_app.py``;
when frozen, :mod:`print_operations` launches this executable again with the
``--print-worker`` arguments.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from react_shell.local_bridge import main as run_bridge


def main(argv: Sequence[str] | None = None) -> int:
    """Run the HTTP bridge, or the hidden local print worker when requested."""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--print-worker", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--printer", default="", help=argparse.SUPPRESS)
    parser.add_argument("--copies", type=int, default=1, help=argparse.SUPPRESS)
    parser.add_argument("--pages", default=None, help=argparse.SUPPRESS)
    args, bridge_args = parser.parse_known_args(argv)

    if args.print_worker:
        from thai_pdf_editor.app.core.print_operations import run_print_worker

        return run_print_worker(
            args.print_worker,
            args.printer,
            copies=args.copies,
            pages=args.pages,
        )
    return run_bridge(bridge_args)


if __name__ == "__main__":
    raise SystemExit(main())
