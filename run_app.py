# -*- coding: utf-8 -*-
"""Run Thai Local PDF Editor."""

import argparse


def main() -> None:
    """Parse CLI flags and start the app."""
    parser = argparse.ArgumentParser(description="Thai Local PDF Editor")
    parser.add_argument("--smoke-test", action="store_true", help="create and close the window automatically")
    parser.add_argument("--print-worker", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--printer", default="", help=argparse.SUPPRESS)
    parser.add_argument("--copies", type=int, default=1, help=argparse.SUPPRESS)
    parser.add_argument("file", nargs="?", default=None, help="PDF file path to open on startup")
    args = parser.parse_args()

    if args.print_worker:
        from thai_pdf_editor.app.core.print_operations import run_print_worker
        from thai_pdf_editor.app.logging_config import setup_logging
        from thai_pdf_editor.app.utils.path_utils import ensure_app_dirs

        ensure_app_dirs()
        setup_logging()
        raise SystemExit(run_print_worker(args.print_worker, args.printer, copies=args.copies))

    from thai_pdf_editor.app.main import run

    run(smoke_test=args.smoke_test, open_file=args.file)


if __name__ == "__main__":
    main()
