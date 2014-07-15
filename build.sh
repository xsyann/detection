#!/usr/bin/env bash
##
## build.sh
##
## Made by xs_yann
## Contact <contact@xsyann.com>
##
## Started on  Fri Apr 25 18:30:49 2014 xs_yann
## Last update Fri Jun  6 11:52:30 2014 xs_yann
##

# Mac application, see py2exe for Windows
sudo rm -rf build dist && sudo python setup.py py2app -A

# Build documentation
epydoc --conf docs/epydoc.conf
