#!/usr/bin/env python3


# 1st-party
import calendar
import datetime
import json
import logging
import os
import sys

# 2nd-party
import package_cache


OUTPUT_DIR = '/var/experiments-output/'
# Data source 3: A map of a project to the date (not time) of when it last
# added, updated or removed a package.
PACKAGE_LAST_MODIFIED_FILENAME = os.path.join(OUTPUT_DIR, 'package_cache.json')
# The experiment is only valid since the following Unix timestamp.
SINCE_TIMESTAMP = 1395360000
SINCE_DATETIME = datetime.datetime.utcfromtimestamp(SINCE_TIMESTAMP)


def assert_datetime_has_no_time(some_datetime):
  assert some_datetime.hour == 0
  assert some_datetime.minute == 0
  assert some_datetime.second == 0
  assert some_datetime.microsecond == 0
  assert some_datetime.tzinfo is None


def get_timestamp_before_compromise(time_delta):
  assert_datetime_has_no_time(SINCE_DATETIME)

  before_datetime = SINCE_DATETIME-time_delta
  assert_datetime_has_no_time(before_datetime)
  assert before_datetime <= SINCE_DATETIME

  # NOTE: necessary to get GMT timestamp from a "naive" datetime object
  return calendar.timegm(before_datetime.utctimetuple())


def partition(earliest_signing_of_claimed_projects_timedelta):
  safe_packages, unsafe_packages = set(), set()

  earliest_signing_of_claimed_projects_timestamp = \
                              get_timestamp_before_compromise(
                                earliest_signing_of_claimed_projects_timedelta)
  assert earliest_signing_of_claimed_projects_timestamp < SINCE_TIMESTAMP
  earliest_signing_of_claimed_projects_datetime = \
                              datetime.datetime.utcfromtimestamp(
                                earliest_signing_of_claimed_projects_timestamp)

  logging.info('Projects that updated on or after {} ({} ago) '\
               'but before {} are considered claimed'\
               .format(earliest_signing_of_claimed_projects_datetime,
                       earliest_signing_of_claimed_projects_timedelta,
                       SINCE_DATETIME))

  with open(PACKAGE_LAST_MODIFIED_FILENAME, 'rt') as fp:
    packages_list = json.load(fp)

    for package in packages_list:
      # Get timestamps of when the project added/updated/removed a package.
      package_timestamps = packages_list[package]
      # Get timestamp, if ANY, of when the project LAST added/updated/removed a
      # package BEFORE the compromise.
      package_timestamp = \
        package_cache.get_last_timestamp_before_compromise(package_timestamps,
                                                           SINCE_TIMESTAMP)

      if package_timestamp:
        if earliest_signing_of_claimed_projects_timestamp <= package_timestamp and \
           package_timestamp < SINCE_TIMESTAMP:
          safe_packages.add(package)
        else:
          unsafe_packages.add(package)
      else:
        unsafe_packages.add(package)

  assert len(safe_packages & unsafe_packages) == 0
  logging.info('Safe time-claimed projects: {:,}'.format(len(safe_packages)))
  logging.info('Vuln time-claimed projects: {:,}'.format(len(unsafe_packages)))

  return safe_packages, unsafe_packages


if __name__ == '__main__':
  # rw for owner and group but not others
  os.umask(0o07)

  # What is the number of days with which to partition packages?
  assert len(sys.argv) == 2
  number_of_days = int(sys.argv[1])
  assert number_of_days > 0
  time_delta = datetime.timedelta(days=int(sys.argv[1]))

  safe_packages, unsafe_packages = partition(time_delta)
  safe_packages = sorted(list(safe_packages))
  unsafe_packages = sorted(list(unsafe_packages))

  output_json_filename = 'partition_packages_by_time.{}days.json'\
                         .format(time_delta.days)
  output_json_filename = os.path.join(OUTPUT_DIR, output_json_filename)
  output_json = {'safe': safe_packages, 'unsafe': unsafe_packages}

  with open(output_json_filename, 'wt') as output_json_file:
    json.dump(output_json, output_json_file, sort_keys=True, indent=4,
              separators=(',', ': '))


