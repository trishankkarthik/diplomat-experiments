#!/usr/bin/env python3


'''
A microbenchmark for measuring the worst-case preorder DFS time for processing
delegations.
'''


# 1st-party
import binascii
import datetime
import errno
import glob
import hashlib
import json
import os
import random
import re


# 2nd-party
from nouns import PACKAGES_DIRECTORY, PYPI_DIRECTORY, SIMPLE_DIRECTORY


CLAIMED_PROJECTS = None
RARELY_UPDATED_PROJECTS = None
NEW_PROJECTS = None
UNCLAIMED_PROJECTS = None
OUTPUT_DIR = '/var/experiments-output/preorder-dfs-microbenchmark/'
ROLE_TO_BACKTRACK = {}
ROLE_TO_KEYIDS = {}
ROLE_TO_PATHS = {}
KEYID_TO_KEYVAL = {}


# Expires this many days from this UTC timestamp.
# Use the Javascript ISO 8601 format.
def make_expiration_timestamp(timestamp, days):
  expires = datetime.datetime.utcfromtimestamp(timestamp)+\
            datetime.timedelta(days=days)
  return expires.isoformat()+'Z'


# Deterministic generation of "signature" given the same filenames, timestamp,
# and version number.
# EITHER the filenames, timestamp, OR the version number MUST change in order
# for the entire signature to change.
def make_pseudo_signature(filenames, timestamp, version):
  change = '{}{}{}'.format(''.join(sorted(filenames)), timestamp, version)
  # Concatenate two 64-byte hashes to get one 128-byte "signature".
  first_half = get_sha256(change.encode('utf-8'))
  second_half = get_sha256(first_half.encode('utf-8'))
  return first_half+second_half


def make_targets_metadata(keyids=(), roles=(), targets={}, timestamp=0,
                          version=0):
  role_keyids = []
  for role in roles:
    role_keyids.extend(ROLE_TO_KEYIDS[role])

  return {
    'signatures': [
      {
        'keyid': keyid,
        'method': 'ed25519',
        'sig': make_pseudo_signature(targets, timestamp, version)
      } for keyid in keyids
    ],
    'signed': {
      '_type': 'Targets',
      'delegations': {
        'keys': {
          keyid: {
            'keytype': 'ed25519',
            'keyval': {
              'public': KEYID_TO_KEYVAL[keyid]
            }
          } for keyid in role_keyids
        },
        'roles': [
          {
            'backtrack': ROLE_TO_BACKTRACK[role],
            'keyids': ROLE_TO_KEYIDS[role],
            'name': role,
            'paths': sorted(ROLE_TO_PATHS[role]),
            'threshold': 1
          } for role in roles
        ]
      },
      # Expire a year from now, following PEP 458.
      'expires': make_expiration_timestamp(timestamp, 365),
      'targets': targets,
      'version': version
    }
  }


def mkdir(directory):
  try:
    os.makedirs(directory)
  except OSError as os_error:
    if os_error.errno != errno.EEXIST:
      raise


def get_random_keyid():
  return get_random_hexstring(64)


def get_random_ed25519_keyval():
  return get_random_hexstring(64)


def get_random_hexstring(length_in_hex):
  assert length_in_hex % 2 == 0
  return binascii.b2a_hex(os.urandom(int(length_in_hex/2))).decode('utf-8')


def get_random_sha256():
  return get_random_hexstring(64)


def get_sha256(data):
  return hashlib.sha256(data).hexdigest()


def get_target_metadata(sha256, length):
  assert length >= 0

  return {
    'hashes': {
      'sha256': sha256
    },
    'length': length
  }


def get_projects():
  global CLAIMED_PROJECTS
  global RARELY_UPDATED_PROJECTS
  global NEW_PROJECTS
  global UNCLAIMED_PROJECTS
  NUMBER_OF_DELEGATEES = 1

  projects = os.listdir(SIMPLE_DIRECTORY)
  random.shuffle(projects)
  assert len(projects) % NUMBER_OF_DELEGATEES == 0
  i = len(projects) // NUMBER_OF_DELEGATEES
  CLAIMED_PROJECTS = projects[:i]
  RARELY_UPDATED_PROJECTS = projects[i:i*2]
  NEW_PROJECTS = projects[i*2:i*3]
  UNCLAIMED_PROJECTS = projects[i*3:]
  assert len(CLAIMED_PROJECTS) + \
         len(RARELY_UPDATED_PROJECTS) + \
         len(NEW_PROJECTS) + \
         len(UNCLAIMED_PROJECTS) == len(projects)


def write_json_to_disk(metadata_path, metadata_dict):
  assert metadata_path.endswith('.json')
  assert isinstance(metadata_dict, dict)

  metadata_path = os.path.join(OUTPUT_DIR, metadata_path)
  dirname = os.path.dirname(metadata_path)
  mkdir(dirname)

  with open(metadata_path, 'wt') as metadata_file:
    json.dump(metadata_dict, metadata_file, indent=1, sort_keys=True)
  print('W {}'.format(metadata_path))


def associate(role, paths, backtrack=True):
  global KEYID_TO_KEYVAL
  global ROLE_TO_KEYIDS
  global ROLE_TO_PATHS

  keyid = get_random_keyid()
  keyval = get_random_ed25519_keyval()

  assert isinstance(backtrack, bool)
  ROLE_TO_BACKTRACK[role] = backtrack

  assert role not in ROLE_TO_KEYIDS
  ROLE_TO_KEYIDS[role] = [keyid]

  assert keyid not in KEYID_TO_KEYVAL
  KEYID_TO_KEYVAL[keyid] = keyval

  assert role not in ROLE_TO_PATHS
  assert isinstance(paths, list)
  ROLE_TO_PATHS[role] = paths


def make_keys():
  associate('projects', ['.*'])

  associate('projects/claimed-projects', ['.*'])
  for project in CLAIMED_PROJECTS:
    associate('projects/claimed-projects/{}'.format(project),
              ['packages/.*/.*/{}/.*'.format(project)], backtrack=False)

  associate('projects/rarely-updated-projects',
            ['packages/.*/.*/{}/.*'.format(project) \
             for project in RARELY_UPDATED_PROJECTS], backtrack=False)

  associate('projects/new-projects', ['.*'])
  for project in NEW_PROJECTS:
    associate('projects/new-projects/{}'.format(project),
              ['packages/.*/.*/{}/.*'.format(project)], backtrack=False)

  associate('projects/unclaimed-projects', ['.*'])


def get_targets(projects):
  targets = {}
  for project in projects:
    packages_directory = os.path.join(PACKAGES_DIRECTORY,
                                      '*/*/{}/*'.format(project))
    # NOTE: With PyPI renaming/canonical-ization of project names,
    # simple names may not directly correspond to package names. What this
    # means is that there may seem to be no packages for renamed projects.
    for package in sorted(glob.glob(packages_directory)):
      sha256 = get_random_sha256()
      length = os.path.getsize(package)
      targets[package] = get_target_metadata(sha256, length)
  return targets


def write():
  keyids = ROLE_TO_KEYIDS['projects']
  roles = ('projects/claimed-projects', 'projects/rarely-updated-projects',
           'projects/new-projects', 'projects/unclaimed-projects')
  metadata_dict = make_targets_metadata(keyids, roles)
  write_json_to_disk('projects.json', metadata_dict)

  keyids = ROLE_TO_KEYIDS['projects/claimed-projects']
  roles = ['projects/claimed-projects/{}'.format(project) \
           for project in CLAIMED_PROJECTS]
  metadata_dict = make_targets_metadata(keyids, roles)
  write_json_to_disk('projects/claimed-projects.json', metadata_dict)

  keyids = ROLE_TO_KEYIDS['projects/rarely-updated-projects']
  roles = ()
  targets = get_targets(RARELY_UPDATED_PROJECTS)
  metadata_dict = make_targets_metadata(keyids, roles, targets)
  write_json_to_disk('projects/rarely-updated-projects.json', metadata_dict)

  keyids = ROLE_TO_KEYIDS['projects/new-projects']
  roles = ['projects/new-projects/{}'.format(project) \
           for project in NEW_PROJECTS]
  metadata_dict = make_targets_metadata(keyids, roles)
  write_json_to_disk('projects/new-projects.json', metadata_dict)

  keyids = ROLE_TO_KEYIDS['projects/unclaimed-projects']
  roles = ()
  targets = get_targets(UNCLAIMED_PROJECTS)
  metadata_dict = make_targets_metadata(keyids, roles, targets)
  write_json_to_disk('projects/unclaimed-projects.json', metadata_dict)


def preorder_dfs(role, package):
  print(role)

  metadata_path = os.path.join(OUTPUT_DIR, '{}.json'.format(role))
  with open(metadata_path) as metadata_file:
    metadata = json.load(metadata_file)

  signatures = metadata['signatures']
  signed = metadata['signed']
  delegations = signed['delegations']
  keys = delegations['keys']
  roles = delegations['roles']
  targets = signed['targets']

  # Preorder: do I know about it?
  target = targets.get(os.path.join(PYPI_DIRECTORY, package))
  if target:
    return target
  # Do delegatees have it?
  else:
    # Ask delegatees in order of priority/appearance.
    for role in roles:
      backtrack = role['backtrack']
      name = role['name']
      paths = role['paths']
      # Have I delegated it to this delegatee?
      for path in paths:
        if re.match(path, package):
          target = preorder_dfs(name, package)
          # Does this delegatee know about it?
          if target:
            return target
          # If not, should I ask the rest of the delegatees?
          elif not backtrack:
            return None
    # Nobody else left to ask.
    else:
      return None

if __name__ == '__main__':
  # Write the delegations.
  #get_projects()
  #make_keys()
  #write()

  # claimed-projects
  preorder_dfs("projects", "packages/source/c/chem/chem-2.0.tar.gz")
  # rarely-updated-projects
  #preorder_dfs("projects", "packages/source/z/zyzz/zyzz-1.0.1.tar.gz")
  # new-projects
  #preorder_dfs("projects", "packages/source/a/agree/agree.tar.gz")
  # unclaimed-projects
  preorder_dfs("projects", "packages/source/z/zzz/zzz-0.0.2.tar.gz")
