#!/usr/bin/env bash

if command -v python &>/dev/null
then
    python main.py
else
    echo "Python is not installed"
fi