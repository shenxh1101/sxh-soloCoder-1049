"""允许通过 python -m studyplan 运行"""
import sys
import os

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

from .cli import cli

if __name__ == "__main__":
    cli()
