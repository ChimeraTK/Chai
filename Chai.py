#!/usr/bin/env python3
import argparse
import os
from pathlib import Path

from chai.MainApp import LayoutApp


def dir_path(path):
    if os.path.isdir(path):
        return path
    else:
        raise argparse.ArgumentTypeError(f"{path} is not a valid path")


def file_path(file_path):
    if os.path.isfile(file_path):
        return file_path
    else:
        raise argparse.ArgumentTypeError(f"{file_path} is not a valid file path")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--root_dir", nargs="?", default=os.getcwd(), type=dir_path, required=False,
                        help="Root directory of the dmap file picker, defaults to current directory")
    parser.add_argument("dmap_file", nargs="?", default=None, type=file_path,
                        help="Path of the dmap file to be loaded on startup")
    args = parser.parse_args()
    app = LayoutApp(args.root_dir, args.dmap_file)
    app.run()
