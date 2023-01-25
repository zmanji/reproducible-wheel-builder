#!/usr/bin/env python3

import argparse
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import build
import pex.bin.pex


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--lock",
        type=lambda p: Path(p).resolve(strict=True),
        help="Path to the pex lock file",
        required=True,
    )
    parser.add_argument(
        "--src",
        type=lambda p: Path(p).resolve(strict=True),
        help="Path to the source directory to build",
        required=True,
    )

    parser.add_argument(
        "--dist",
        help="Type of distribution to build",
        default="wheel",
        choices=["wheel", "sdist", "editable"],
    )

    parser.add_argument(
        "--out",
        type=lambda p: Path(p).resolve(),
        help="Path to the output directory",
        required=True,
    )

    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Supress the output of the build backend",
    )

    parser.add_argument(
        "--requires_config",
        type=lambda p: json.loads(Path(p).read_bytes()),
        default={},
        help="JSON file of config to pass to build backend when getting requires",
    )

    parser.add_argument(
        "--build_config",
        type=lambda p: json.loads(Path(p).read_bytes()),
        default={},
        help="JSON file of config to pass to build backend when building",
    )

    args = parser.parse_args()

    td = tempfile.mkdtemp()

    def _runner(cmd, cwd=None, extra_environ=None):
        env = os.environ.copy()
        if extra_environ:
            env.update(extra_environ)

        env.update({"PEX_INTERPRETER": "1"})

        if args.quiet:
            subprocess.check_call(
                cmd,
                cwd=cwd,
                env=env,
                stderr=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
            )
        else:
            print(f"Running: {cmd}", file=sys.stderr)
            subprocess.check_call(cmd, cwd=cwd, env=env)

    def _pex(reqs):
        pex_args = [
            "--lock",
            str(args.lock),
            "--no-compress",
            "--seed=verbose",
            "--venv=prepend",
            "--no-build",
            "-o",
            td + "/out.pex",
        ]
        pex_args = pex_args + list(reqs)
        if not args.quiet:
            print(f"Running pex: {pex_args}", file=sys.stderr)

        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            try:
                pex.bin.pex.main(pex_args)
            except SystemExit as e:
                if e.code:
                    print(f"Failed to run pex: {pex_args}", file=sys.stderr)
                    raise e

        seed = json.loads(stdout.getvalue())["pex"]
        return seed

    builder = build.ProjectBuilder(
        args.src, python_executable=sys.executable, runner=_runner
    )
    # Create the initial pex file

    exe = _pex(builder.build_system_requires)

    builder = build.ProjectBuilder(args.src, python_executable=exe, runner=_runner)

    dependencies = builder.get_requires_for_build(
        args.dist, config_settings=args.requires_config
    ).union(builder.build_system_requires)

    if dependencies != builder.build_system_requires:
        exe = _pex(dependencies)

    builder = build.ProjectBuilder(args.src, python_executable=exe, runner=_runner)

    whl = builder.build(args.dist, args.out, config_settings=args.build_config)

    shutil.rmtree(td)

    print(f"{whl}")


if __name__ == "__main__":
    main()
