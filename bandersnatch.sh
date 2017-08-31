#!/bin/bash

# http://unix.stackexchange.com/q/12842
umask 007

virtualenv --no-site-packages pyenv
source pyenv/bin/activate
pip install -U bandersnatch
bandersnatch -c bandersnatch.conf mirror

