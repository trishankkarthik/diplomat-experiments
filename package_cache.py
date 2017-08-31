#!/usr/bin/env python3


# 1st-party
import calendar
from datetime import datetime
import json
import logging
import os
import time
import urllib.request as request
import xmlrpc.client as xmlrpclib

# 3rd-party
# sudo apt-get install python3-bs4
from bs4 import BeautifulSoup


def get_last_timestamp_before_compromise(timestamps, compromise_timestamp):
  last_timestamp_before_compromise = None

  # Walk timestamp in increasing order of time.
  for timestamp in sorted(timestamps):
    # This timestamp is still before the compromise, so keep it instead.
    if timestamp < compromise_timestamp:
      last_timestamp_before_compromise = timestamp
    # Aha, we are now after the compromise. Get out of here.
    else:
      break

  # Return either the last known timestamp before compromise, or None if no
  # timestamp before compromise was observed.
  return last_timestamp_before_compromise


# simple class to store redirections locally, should be initialized from
# a previous file and it will store the redirections in a file.
class pypi_database_builder:


  def __init__(self, filename, rebuild_cache=False):
    # For every project, we get list of timestamps (sorted in increasing order)
    # that the project added/updated/removed some package.
    # {
    #   "Django": [timestamp("May 17 2010"), ..., timestamp("Oct 22 2014")]
    # }
    if os.path.exists(filename):
      with open(filename, 'rt') as fp:
        self.project_to_package_timestamps = json.load(fp)

    else:
      self.project_to_package_timestamps = {}

    self.filename = filename
    self.rebuild_cache = rebuild_cache

    self.throttle_time = 100


  # package_date (e.g. "May 23, 2014") is the date that this project last
  # added, updated or removed a package.
  def get_timestamp(self, package_date):
    # Parse the date as a time.struct_time tuple.
    package_timestruct = time.strptime(package_date, '%b %d, %Y')

    # Turn the time.struct_time tuple into a POSIX timestamp.
    package_timestamp = calendar.timegm(package_timestruct)

    return package_timestamp


  def get_timestamps(self, soup):
    all_versions = soup.select('#all-versions')

    if len(all_versions) > 0:
      assert len(all_versions) == 1
      all_versions = all_versions[0]
      spans = all_versions.select('span.text-muted')

    else:
      metadata_div = soup.select('div.metadata')
      assert len(metadata_div) == 1
      metadata_div = metadata_div[0]
      metadata_terms = metadata_div.find_all('dt')

      for metadata_term in metadata_terms:
        if metadata_term.string == 'Versions':
          versions = metadata_term
          break

      spans = versions.next_sibling.next_sibling.ul.select('span.text-muted')

    dates = {span.string for span in spans}
    timestamps = sorted(self.get_timestamp(date) for date in dates)
    return timestamps


  def build(self):
    projects = xmlrpclib.ServerProxy('https://pypi.python.org/pypi')\
                        .list_packages()
    failure_counter = 0
    success_counter = 0

    for project in projects:
      if self.rebuild_cache or project not in self.project_to_package_timestamps:
        try:
          url = 'https://warehouse.python.org/project/{}/'.format(project)
          soup = BeautifulSoup(request.urlopen(url))
          timestamps = self.get_timestamps(soup)

        except:
          logging.exception('Missed project: {}'.format(project))
          failure_counter += 1

        else:
          self.project_to_package_timestamps[project] = timestamps

          logging.info('Found project: {}'.format(project))
          success_counter += 1

        finally:
          counter = failure_counter+success_counter
          if counter % self.throttle_time == 0:
            progress_rate = (counter/len(projects))*100
            logging.debug('Sleeping for 5 seconds... ({}% complete)'\
                          .format(progress_rate))
            self.dump()
            time.sleep(5)

    counter = failure_counter+success_counter
    assert counter == len(projects)
    failure_percentage = (failure_counter/counter)*100
    failure_message = 'Missed {} ({}%) projects'.format(failure_counter,
                                                        failure_percentage)
    assert failure_percentage < 1, failure_message
    logging.info(failure_message)
    self.dump()


  def dump(self):
    with open(self.filename, 'wt') as fp:
      json.dump(self.project_to_package_timestamps, fp, sort_keys=True,
                indent=4, separators=(',', ': '))


if __name__ == '__main__':
  # rw for owner and group but not others
  os.umask(0o07)

  logging.basicConfig(filename='/var/experiments-output/package_cache.log',
                      level=logging.DEBUG, filemode='w',
                      format='[%(asctime)s UTC] [%(name)s] [%(levelname)s] '\
                             '[%(funcName)s:%(lineno)s@%(filename)s] '\
                             '%(message)s')

  cache = pypi_database_builder('/var/experiments-output/package_cache.json',
                                rebuild_cache=True)
  cache.build()


