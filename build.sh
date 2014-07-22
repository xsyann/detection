#!/usr/bin/env bash
# build.sh
#
# Author: Yann KOETH
# Created: Tue Jul 22 20:27:47 2014 (+0200)
# Last-Updated: Tue Jul 22 20:27:54 2014 (+0200)
#           By: Yann KOETH
#     Update #: 2
#

# Build documentation
epydoc --conf docs/epydoc.conf

# Mac application, see py2exe for Windows
sudo python setup.py py2app
cd dist
sudo macdeployqt *.app #-dmg
cd -
