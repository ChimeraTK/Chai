#!/usr/bin/env python3

from chai.MainApp import LayoutApp
import sys
import os

if __name__ == "__main__":

    if len(sys.argv) > 1:
        if not os.path.isfile(sys.argv[1]):
            print(f'Error: File "{sys.argv[1]}" does not exist!')
            sys.exit(1)

    app = LayoutApp()
    app.run()
