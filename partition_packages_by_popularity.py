#!/usr/bin/env python3


# 1st-party
import json
import logging
import os
import sys


OUTPUT_DIR = '/var/experiments-output/'
# Data source 4: This list is expected to be in order of descending
# popularity.
PACKAGE_POPULARITY_FILENAME = os.path.join(OUTPUT_DIR,
                                           'packages_by_popularity.txt')


# This function returns a tuple of two sets, unsafe and safe, assuming that the
# most popular packages are the ones that are secure.
# The tuple returned will be of the form (safe, unsafe).
def partition(fraction_of_claimed_packages):
  packages_list = []
  prev_count = None

  logging.info('{}% safe popular projects'\
               .format(fraction_of_claimed_packages*100))

  with open(PACKAGE_POPULARITY_FILENAME, 'rt') as fp:
    for line in fp:
      package, count = line.split(',')

      count = int(count)
      assert count >= 0
      if prev_count is None:
        prev_count = count
      assert prev_count >= count
      prev_count = count

      assert len(package) > 0
      packages_list.append(package)

  assert fraction_of_claimed_packages >= 0
  assert fraction_of_claimed_packages <= 1
  num_secure_packages = round(fraction_of_claimed_packages*len(packages_list))

  safe_packages = set(packages_list[:num_secure_packages])
  unsafe_packages = set(packages_list[num_secure_packages:])
  assert len(safe_packages) + len(unsafe_packages) == len(packages_list)
  assert len(safe_packages & unsafe_packages) == 0

  logging.info('Safe popular projects: {:,}'.format(len(safe_packages)))
  logging.info('Vuln unpopular projects: {:,}'.format(len(unsafe_packages)))

  return safe_packages, unsafe_packages


if __name__ == '__main__':
  # rw for owner and group but not others
  os.umask(0o07)

  # What is the fraction of popularity?
  assert len(sys.argv) == 2
  fraction_of_claimed_packages = float(sys.argv[1])

  safe_packages, unsafe_packages = partition(fraction_of_claimed_packages)
  safe_packages = sorted(list(safe_packages))
  unsafe_packages = sorted(list(unsafe_packages))

  output_json_filename = 'partition_packages_by_popularity.{}%.json'\
                         .format(round(fraction_of_claimed_packages*100))
  output_json_filename = os.path.join(OUTPUT_DIR, output_json_filename)
  output_json = {'safe': safe_packages, 'unsafe': unsafe_packages}

  with open(output_json_filename, 'wt') as output_json_file:
    json.dump(output_json, output_json_file, sort_keys=True, indent=4,
              separators=(',', ': '))


