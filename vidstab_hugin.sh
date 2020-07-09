#!/usr/bin/sh

python=python3

BASEDIR=$(dirname "$0")
python $BASEDIR/src/vidstab_hugin.py $@
