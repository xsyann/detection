#!/usr/bin/env python
# -*- coding: utf-8 -*-
# flip.py
#
# Author: Yann KOETH
# Created: Sun Jul 20 15:13:51 2014 (+0200)
# Last-Updated: Sun Jul 20 15:32:45 2014 (+0200)
#           By: Yann KOETH
#     Update #: 24
#

import os
import glob
import cv2
import argparse, sys

def main():

    parser = argparse.ArgumentParser(description="Flip all images in folder.")
    parser.add_argument("folder", help="Folder path")
    args = parser.parse_args()

    samples = glob.glob(args.folder + "/*.jpg")
    for sample in samples:
        img = cv2.imread(sample)
        flipped = cv2.flip(img, 1, img)
        fn, ext = os.path.splitext(sample)
        name = fn + "-flipped" + ext
        cv2.imshow("flipped", flipped)
        print name
#        cv2.imwrite(name, flipped)

if __name__ == '__main__':
    main()
