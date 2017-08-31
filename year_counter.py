#!/usr/bin/env python3


import collections
import csv
from datetime import datetime
import json

import translation_cache
import package_cache


PACKAGE_TIMESTAMPS_FILENAME = '/var/experiments-output/package_cache.json'
DOWNLOAD_LOG_FILENAME = '/var/experiments-output/simple/sorted.packages.log.4'

# The experiment is only valid since the following Unix timestamp.
SINCE_TIMESTAMP = 1395360000
UNTIL_TIMESTAMP = 1397952000


with open(PACKAGE_TIMESTAMPS_FILENAME) as package_timestamps_json:
  project_timestamps = json.load(package_timestamps_json)

projects_last_updated_in_year = collections.Counter()
projects_last_updated_in_2014_last_updated_in_month = collections.Counter()

for timestamps in project_timestamps.values():
  # We are looking only at projects did update before compromise.
  last_updated_timestamp = \
            package_cache.get_last_timestamp_before_compromise(timestamps,
                                                               SINCE_TIMESTAMP)

  if last_updated_timestamp:
    last_updated_datetime = datetime.utcfromtimestamp(last_updated_timestamp)
    last_updated_year = last_updated_datetime.year
    projects_last_updated_in_year[last_updated_year] += 1

    if last_updated_year == 2014:
      last_updated_month = last_updated_datetime.month
      projects_last_updated_in_2014_last_updated_in_month[
                                                      last_updated_month] += 1

print('All projects last updated before compromise in these years:')
print(projects_last_updated_in_year)
print('')

print('All projects last updated before compromise in 2014 updated in these months:')
print(projects_last_updated_in_2014_last_updated_in_month)
print('')

dloaded_projects_last_updated_in_year = collections.Counter()
dloaded_projects_last_updated_in_2014_last_updated_in_month = \
                                                        collections.Counter()
future_projects = set()
missing_projects = set()

with open(DOWNLOAD_LOG_FILENAME) as download_log:
  download_log = csv.reader(download_log)

  for timestamp, ip_address, package_url, user_agent in download_log:
    timestamp = int(timestamp)
    project_name = translation_cache.infer_package_name(package_url)

    try:
      timestamps = project_timestamps[project_name]
    except KeyError:
      # NOTE: Probably the entire project was deleted after compromise but
      # before now.
      missing_projects.add(project_name)
      continue
    else:
      # We are looking only at projects did update before compromise.
      last_updated_timestamp = \
            package_cache.get_last_timestamp_before_compromise(timestamps,
                                                               SINCE_TIMESTAMP)

      # Project was not updated before compromise.
      if not last_updated_timestamp:
        # Misnomer, but actually the first time package was updated after
        # compromise.
        last_updated_timestamp = timestamps[0]

        # Question: Why is the user downloading a package from a project that
        # *seems* to have been last updated in the future?
        # Answer: Some of these packages seem to have been deleted.  For
        # example, a user downloaded sparsehash-0.11 which does not exist on
        # PyPI anymore, and the earliest known package now is sparsehash-0.3
        # which was updated after the compromise.
        if last_updated_timestamp > UNTIL_TIMESTAMP:
          future_projects.add(project_name)

      last_updated_datetime = \
                            datetime.utcfromtimestamp(last_updated_timestamp)
      last_updated_year = last_updated_datetime.year
      dloaded_projects_last_updated_in_year[last_updated_year] += 1

      if last_updated_year == 2014:
        last_updated_month = last_updated_datetime.month
        dloaded_projects_last_updated_in_2014_last_updated_in_month[
                                                    last_updated_month] += 1

print('All downloaded projects were last updated in these years:')
print(dloaded_projects_last_updated_in_year)
print('')

print('All downloaded projects last updated in 2014 updated in these months:')
print(dloaded_projects_last_updated_in_2014_last_updated_in_month)
print('')

print('Projects that seem to be from the future:')
print(sorted(future_projects))
print('')

print('Missing (deleted?) projects:')
print(sorted(missing_projects))
print('')

