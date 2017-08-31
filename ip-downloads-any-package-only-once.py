#!/usr/bin/env python3

import collections
import sys

# {
#   "127.0.0.1": {
#       "Django-1.5.tar.gz": 42,
#       "virtualenv-1.7.tar.gz": 1
#   }
# }
ips = {}

assert len(sys.argv) == 2
filename = sys.argv[1]

with open(filename, 'rt') as log:
  for request in log:
    ip, package = request.split(',')
    ips.setdefault(ip, collections.Counter())[package] += 1

for ip, packages in ips.items():
  # If the IP has downloaded each package only once, then the total number of
  # downloads will be equal to the number of different packages the user
  # downloaded.
  if sum(packages.values()) == len(packages):
    print(ip)

