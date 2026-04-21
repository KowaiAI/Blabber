#!/usr/bin/env python3
import sys
import os

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(__file__))

from blabber.app import BlabberApp


def main():
    app = BlabberApp()
    app.run()


if __name__ == "__main__":
    main()
