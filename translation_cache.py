#!/usr/bin/env python3


# 1st-party
import json
import lzma
import os
import re
import urllib.error
import urllib.request

import xmlrpc.client as xmlrpclib


EPSILON = ''
SLASH = '/'

PROJECT_URL_REGEX = re.compile(r'^/packages/(.+)/(.+)/(.+)/(.+)$')

TRANSLATION_CACHE_FILENAME = '/var/experiments-output/translation_cache.json'
SIMPLE_LOG_FILENAME = '/var/experiments-output/simple/sorted.simple.log.xz'


def infer_package_name(path):
  url = path.strip().strip('"')
  project_name = PROJECT_URL_REGEX.match(url).group(3).strip(SLASH)
  assert len(project_name) > 0
  assert SLASH not in project_name
  return project_name


# simple class to store redirections locally, should be initialized from
# a previous file and it will store the redirections in a file.
class pypi_translation_cache:


  def __init__(self, should_translate_from_upstream=False,
               filename=TRANSLATION_CACHE_FILENAME):
    self.should_translate_from_upstream = should_translate_from_upstream

    if os.path.exists(filename):
      with open(filename, 'rt') as fp:
        self.translation_dict = json.load(fp)
    else:
      self.translation_dict = {}


  def translate(self, project_name):
    if project_name in self.translation_dict:
      return self.translation_dict[project_name]

    elif self.should_translate_from_upstream:
      req = urllib2.request.Request('https://pypi.python.org/simple/{}/'.\
                                    format(project_name))
      # http://stackoverflow.com/a/4421485
      req.get_method = lambda: 'HEAD'

      try:
        res = urllib2.request.urlopen(req)
        redirection = res.geturl()
        translated_name = re.match('^https://pypi.python.org/simple/([^/]*)/$',
                                   redirection).group(1).strip(SLASH)
        assert SLASH not in translated_name

      except urllib2.error.HTTPError as e:
        translated_name = None

      self.translation_dict[project_name] = translated_name
      return translated_name

    else:
      return None


  def dump(self, filename):
    with open(filename, 'wt') as fp:
      json.dump(self.translation_dict, fp)


# since the first time the cache takes a while to populate, we should 
# run this script to initialize the local file.
def _build_redirection_cache():
  cache = pypi_translation_cache(True)
  minicache = set() 

  with lzma.open(SIMPLE_LOG_FILENAME, 'rt') as fp:
    i = 0

    for event in fp:
      try:
        request = event.split(',')[2]
        package_name = infer_package_name(request)
        result = cache.translate(package_name)

      except Exception as e:
        cache.dump(filename)
        print("{}: {}".format(i, e))
        raise

      i += 1

      if result is None and result not in minicache:
        print("Not found: {}".format(package_name))
        minicache.add(result)

      if i % 10000 == 0:
        print("=============================")
        print(" At line: {}".format(i))
        print("=============================")

  cache.dump(filename)


if __name__ == '__main__':
  # rw for owner and group but not others
  os.umask(0o07)

  _build_redirection_cache()


