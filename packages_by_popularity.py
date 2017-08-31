#!/usr/bin/env python3


# 1st-party
import collections
import csv
import json
import logging
import os
import sys

# 2nd-party
import package_cache
import translation_cache

# Data source 3: A map of a project to the date (not time) of when it last
# added, updated or removed a package.
PACKAGE_LAST_MODIFIED_FILENAME = '/var/experiments-output/package_cache.json'

# The time since the hypothetical compromise began (i.e. since the download log
# began).
SINCE_TIMESTAMP = 1395360000


# this script will traverse the filename in the format of sorted.simple.log
# and count the instances of every package request that occurred. 
def sort_packages_by_popularity(filename):
  packages = collections.Counter()

  # Zero counters for all projects estimated to exist before compromise.
  with open(PACKAGE_LAST_MODIFIED_FILENAME, 'rt') as fp:
    packages_list = json.load(fp)

    for package in packages_list:
      # Get timestamps of when the project added/updated/removed a package.
      timestamps = packages_list[package]
      timestamp = \
        package_cache.get_last_timestamp_before_compromise(timestamps,
                                                           SINCE_TIMESTAMP)

      # This project was updated sometime before compromise.
      # That means this project can be included in the set of projects that
      # existed before compromise, giving us a better estimate of the true
      # number of projects that existed just before compromise.
      if timestamp:
        assert timestamp < SINCE_TIMESTAMP
        packages[package] = 0

  logging.info('# of projects estimated to exist before compromise: {:,}'\
               .format(len(packages)))

  # Now count the popularity of packages that were actually downloaded.
  # NOTE: This is extremely biased towards the compromise period, but we have
  # no better data. Must note in paper.
  with open(filename, 'rt') as simple_log:
    requests = csv.reader(simple_log)

    for timestamp, anonymized_ip, request, user_agent in requests:
      package_name = translation_cache.infer_package_name(request)
      assert package_name
      assert len(package_name) > 0, request
      packages[package_name] += 1

  # order the dictionary
  logging.info('total # projects seen to exist after compromise: {:,}'\
               .format(len(packages)))

  with open('/var/experiments-output/packages_by_popularity.txt', 'wt') as \
                                                        ordered_packages_file:
    for package, count in packages.most_common():
      assert len(package) > 0
      ordered_packages_file.write("{},{}\n".format(package, count))


if __name__ == '__main__':
  # rw for owner and group but not others
  os.umask(0o07)

  assert len(sys.argv) == 2
  log_filename = sys.argv[1]

  sort_packages_by_popularity(log_filename)


