#!/usr/bin/env python3

import collections
import sys

ips = {}
n = 100

assert len(sys.argv) == 2
filename = sys.argv[1]

with open(filename, 'rt') as log:
  for request in log:
    ip, package = request.split(',')
    ips.setdefault(ip, collections.Counter())[package] += 1

for ip, packages in ips.items():
  # If the user has downloaded up to n packages, then keep this user.
  if len(packages) <= n:
    print(ip)

