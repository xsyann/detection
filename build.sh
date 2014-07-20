#!/usr/bin/env bash
##
## build.sh
##
## Made by xs_yann
## Contact <contact@xsyann.com>
##
## Started on  Fri Apr 25 18:30:49 2014 xs_yann
## Last update Sun Jul 20 21:37:04 2014 xs_yann
##

# Build documentation
epydoc --conf docs/epydoc.conf

# Mac application, see py2exe for Windows
sudo python setup.py py2app
cd dist
sudo macdeployqt *.app #-dmg
cd -
