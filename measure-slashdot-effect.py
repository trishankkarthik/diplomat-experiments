#!/usr/bin/env python3


# 1st-party
import collections
import csv
import lzma
import os
import re


CHANGELOG_FILENAME = '/var/experiments-output/1395360000-1397952000.changelog'
SORTED_SIMPLE_LOG_FILENAME = \
  '/var/experiments-output/simple/sorted.simple.log.xz'


def get_new_projects_from_changelog():
  projects = set()

  with open(CHANGELOG_FILENAME, 'rt') as changelog_file:
    for line in changelog_file:
      name, version, timestamp, action, serial = line.split(';')

      if action == 'create':
        projects.add(name)

  return projects


def get_new_packages_from_changelog(projects):
  packages = set()

  with open(CHANGELOG_FILENAME, 'rt') as changelog_file:
    for line in changelog_file:
      name, version, timestamp, action, serial = line.split(';')
      action_match = re.match(r'^add (.+) file (.+)$', action)

      if action_match and name in projects:
        pyversion, filename = action_match.groups()
        packages.add(filename)

  return packages
 

def measure(packages):
  package_downloads = collections.Counter()

  with lzma.open(SORTED_SIMPLE_LOG_FILENAME, 'rt') as sorted_simple_log_file:
    sorted_simple_log_file = csv.reader(sorted_simple_log_file)

    for line in sorted_simple_log_file:
      unix_timestamp, ip_address, url, user_agent = line

      if url.startswith('/packages/'):
        filename = os.path.basename(url)

        if filename in packages:
          package_downloads[filename] += 1

  return package_downloads.most_common()
 

def count(package, max_timestamp, total_downloads):
  with lzma.open(SORTED_SIMPLE_LOG_FILENAME, 'rt') as sorted_simple_log_file:
    sorted_simple_log_file = csv.reader(sorted_simple_log_file)
    counter = 0

    for line in sorted_simple_log_file:
      unix_timestamp, ip_address, url, user_agent = line
      unix_timestamp = int(unix_timestamp)

      if url == package:
        counter += 1
        percent = (counter / total_downloads) * 100

        # The danger of dynamic typing: Python will happily compare a string
        # with an integer without any warning.
        if unix_timestamp > max_timestamp:
          print('{} {} {}%'.format(unix_timestamp, counter, percent))
          break


if __name__ == '__main__':
  #projects = get_new_projects_from_changelog()
  #print(sorted(projects))
  #print()

  #packages = get_new_packages_from_changelog(projects)
  #print(sorted(packages))
  #print()

  #package_downloads = measure(packages)
  #print(package_downloads)
  #print()

  # Found to be the most downloaded new package.
  most_downloaded_new_package = '/packages/source/d/django-cms/django-cms-2.4.3.tar.gz'
  # Offset from time of release.
  max_timestamp = 1397219572 + (1 * 24 * 60 * 60)
  total_downloads = 4170
  count(most_downloaded_new_package, max_timestamp, total_downloads)


