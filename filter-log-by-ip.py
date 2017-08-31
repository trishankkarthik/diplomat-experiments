#!/usr/bin/env python

# Justin Cappos
# The purpose is to filter a log by IP Addresses.  (The second field in the
# log when comma separated.)  This program takes the IP list as the only
# argument and reads the log to filter from stdin.  It writes the output
# to stdout.

import sys

if len(sys.argv) != 2:
  print "Error, must have one argument.  See the doc string."
  sys.exit(1)

setofvalidips = set()

# will get an error if no argument...
for line in file(sys.argv[1]):
  setofvalidips.add(line.strip())

for line in sys.stdin:
  ipfield = line.split(',')[1]
  if ipfield in setofvalidips:
    # remove the trailing CR
    print line.strip()
