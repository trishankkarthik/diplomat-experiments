#!/usr/bin/env python3

'''
Determine from the PyPI change log what projects were added during compromise. 
Given the set of safe and unsafe projects, remove these new projects from the
set of safe projects, and add them instead to the set of unsafe projects.
'''

# 1st-party
import json
import logging
import os
import sys

# 2nd-party
import changelog


# The experiment is only valid since the following Unix timestamp.
SINCE_TIMESTAMP = 1395360000
UNTIL_TIMESTAMP = 1397952000


class ChangeLogReader(changelog.ChangeLogReader):


  def __init__(self, since, until):
    super(ChangeLogReader, self).__init__(since, until)
    self.new_packages = set()


  def handle_create(self, change, action_match):
    super(ChangeLogReader, self).handle_create(change, action_match)

    name, version, timestamp, action, serial = change
    self.new_packages.add(name)


# This function will move the newly created projects from the safe set to the
# unsafe set, simulating the behavior of unclaimed. The idea behind this to
# parse the changelog and remove from the set of safe packages any package that
# was created in the change log and add it instead to the set of unsafe
# projects.
def move(safe_packages, unsafe_packages):
  assert len(safe_packages & unsafe_packages) == 0

  # Data source 2: This is where we see developers creating/deleting projects,
  # adding/deleting packages from their projects, and so on.
  changelog_reader = ChangeLogReader(SINCE_TIMESTAMP, UNTIL_TIMESTAMP)
  assert len(changelog_reader.new_packages) == 0
  changelog_reader.read()
  assert len(changelog_reader.new_packages) > 0
  new_packages = changelog_reader.new_packages

  before_safe_packages_count = len(safe_packages)
  before_unsafe_packages_count = len(unsafe_packages)

  safe_packages -= new_packages
  unsafe_packages |= new_packages

  after_safe_packages_count = len(safe_packages)
  after_unsafe_packages_count = len(unsafe_packages)

  logging.info('Prev Safe: {:,}'.format(before_safe_packages_count))
  logging.info('Prev Vuln: {:,}'.format(before_unsafe_packages_count))

  logging.info('Curr Safe: {:,}'.format(after_safe_packages_count))
  logging.info('Curr Vuln: {:,}'.format(after_unsafe_packages_count))

  assert before_safe_packages_count+before_unsafe_packages_count <= \
         after_safe_packages_count+after_unsafe_packages_count

  logging.info('{:,} raw new projects'.format(len(new_packages)))

  new_safe_packages_count = \
                          after_safe_packages_count-before_safe_packages_count
  logging.info('{:,} new safe projects'.format(new_safe_packages_count))

  new_unsafe_packages_count = \
                      after_unsafe_packages_count-before_unsafe_packages_count
  logging.info('{:,} new unsafe projects'.format(new_unsafe_packages_count))

  new_packages_count = new_safe_packages_count+new_unsafe_packages_count
  logging.info('{:,} effective new projects'.format(new_packages_count))


if __name__ == '__main__':
  # rw for owner and group but not others
  os.umask(0o07)

  assert len(sys.argv) == 3

  # What is the input JSON filename?
  input_json_filename = sys.argv[1]
  assert os.path.isfile(input_json_filename)

  # What is the output JSON filename?
  output_json_filename = sys.argv[2]

  with open(input_json_filename, 'rt') as input_json_file:
    input_json = json.load(input_json_file)

  safe_packages = set(input_json['safe'])
  unsafe_packages = set(input_json['unsafe'])

  move(safe_packages, unsafe_packages)

  safe_packages = sorted(list(safe_packages))
  unsafe_packages = sorted(list(unsafe_packages))
  output_json = {'safe': safe_packages, 'unsafe': unsafe_packages}

  with open(output_json_filename, 'wt') as output_json_file:
    json.dump(output_json, output_json_file, sort_keys=True, indent=4,
              separators=(',', ': '))


