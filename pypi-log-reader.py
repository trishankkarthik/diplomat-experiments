#!/usr/bin/env python3


'''
TODO:
  * Map-reduce the logs, but this is good enough.
'''


# 1st-party
import collections
import csv
import datetime
import logging
import lzma
import os
import re
import sys

# 3rd-party
# apt-get install python3-matplotlib
import matplotlib
# Force matplotlib to not use any Xwindows backend.
# http://stackoverflow.com/a/3054314
matplotlib.use('Agg')
import matplotlib.pyplot
import numpy


class SortedSimplePyPILogReader:
  EPSILON = ''
  SLASH = '/'

  MIN_RANK = 1
  MAX_RANK = 100

  PROJECT_URL_REGEX = re.compile(r'^/packages/(.+)/(.+)/(.+)/(.+)$')


  def __init__(self):
    # ip_address: set(project_name)
    self.ip_address_projects = {}
    # ip_address: request_count
    self.ip_address_requests = collections.Counter()
    # project_name: request_count
    self.package_requests = collections.Counter()

    self.oldest_timestamp = 0
    self.previous_timestamp = 0

  def parse(self, sorted_simple_log_filepath):
    with lzma.open(sorted_simple_log_filepath, 'rt') as sorted_simple_log_file:
      sorted_simple_log_file = csv.reader(sorted_simple_log_file)
      for line in sorted_simple_log_file:
        unix_timestamp, ip_address, url, user_agent = line
        unix_timestamp = int(unix_timestamp)

        assert self.previous_timestamp <= unix_timestamp

        pyversion, alphabet, project_name, package_name = \
                        SortedSimplePyPILogReader.PROJECT_URL_REGEX.match(url)
        project_name = project_name.strip(SortedSimplePyPILogReader.SLASH)
        assert SortedSimplePyPILogReader.SLASH not in project_name

        self.package_requests[project_name] += 1

        self.oldest_timestamp = self.oldest_timestamp or unix_timestamp
        self.previous_timestamp = unix_timestamp
        self.ip_address_requests[ip_address] += 1
        self.ip_address_projects.setdefault(ip_address, set())\
                                .add(project_name)


  def plot_cumulative_client_curve(self, max_rank, num_of_num_of_requests):
    items = sorted(num_of_num_of_requests.items())
    sum_of_num_of_requests = sum(num_of_num_of_requests.values())

    cumulative_num_of_num_of_requests = 0
    cumulative_percent_of_num_of_requests = []
    indices = []

    # compute the percentages of clients accumulated
    for rank in range(max_rank):
      num_of_requests, num_of_num_of_requests = items[rank]
      cumulative_num_of_num_of_requests += num_of_num_of_requests
      cumulative_percent = (cumulative_num_of_num_of_requests / \
                            sum_of_num_of_requests) * 100

      indices.append(num_of_requests)
      cumulative_percent_of_num_of_requests.append(cumulative_percent)

    # plot
    matplotlib.pyplot.plot(indices, cumulative_percent_of_num_of_requests,
                           'r-x')

    # add title, labels, ticks, legends
    matplotlib.pyplot.title('Cumulative percentage of clients who issue\n' \
                            'a given number HTTP requests to PyPI')
    matplotlib.pyplot.ylabel('Cumulative percentage of clients (%)')
    matplotlib.pyplot.xlabel('Number of HTTP requests to PyPI')

    # write the actual plot
    matplotlib.pyplot.savefig('cumulative-client-curve.png')


  def plot_cumulative_request_curve(self, max_rank,
                                    num_of_package_requests_by_rank,
                                    num_of_package_requests):
    cumulative_num_of_package_requests = 0
    min_rank = SortedSimplePyPILogReader.MIN_RANK

    cumulative_percent_of_package_requests_by_rank = []
    indices = numpy.arange(min_rank, min_rank + max_rank)

    # compute the percentages of requests accumulated
    for rank in range(max_rank):
      cumulative_num_of_package_requests += \
        num_of_package_requests_by_rank[rank]

      cumulative_percent_of_package_requests = \
        (cumulative_num_of_package_requests / num_of_package_requests) * 100

      cumulative_percent_of_package_requests_by_rank.\
        append(cumulative_percent_of_package_requests)

    # plot the curves
    package_plot, = \
      matplotlib.pyplot.plot(indices,
                             cumulative_percent_of_package_requests_by_rank,
                             'b-.')
    matplotlib.pyplot.legend([package_plot],
                             ['Package requests'],
                             loc='lower center')

    # add title, labels, ticks, legends
    matplotlib.pyplot.title('Cumulative percentage of requests\n' \
                            'due to popular projects on PyPI')
    matplotlib.pyplot.ylabel('Cumulative percentage of requests (%)')
    matplotlib.pyplot.xlabel('PyPI project rank')
    matplotlib.pyplot.xlim(xmin=min_rank)

    # write the actual plot
    matplotlib.pyplot.savefig('cumulative-request-curve.png')


  def summarize(self):
    max_rank = SortedSimplePyPILogReader.MAX_RANK

    assert self.oldest_timestamp <= self.previous_timestamp
    oldest_datetime = \
      datetime.datetime.utcfromtimestamp(self.oldest_timestamp)
    newest_datetime = \
      datetime.datetime.utcfromtimestamp(self.previous_timestamp)
    seconds_elapsed = self.previous_timestamp - self.oldest_timestamp

    # [('project_name', num_of_requests), ...]
    package_requests = self.package_requests.most_common()
    num_of_package_requests_by_rank = [p[1] for p in package_requests]
    num_of_package_requests = sum(num_of_package_requests_by_rank)

    pop_package_requests = package_requests[:max_rank]
    pop_package_names = set(p[0] for p in pop_package_requests)
    num_of_pop_package_requests_by_rank = [p[1] for p in pop_package_requests]
    num_of_pop_package_requests = sum(num_of_pop_package_requests_by_rank)

    num_of_new_requests = len(self.ip_address_requests)
    num_of_requests = num_of_simple_requests + num_of_package_requests
    # number of times a number of requests is seen
    num_of_num_of_requests = collections.Counter()
    # number of times a number of projects is seen
    num_of_num_of_projects = collections.Counter()

    rate_of_requests = num_of_requests / seconds_elapsed
    logging.info('# of seconds from {} to {}: {:,}s'.format(oldest_datetime,
                                                     newest_datetime,
                                                     seconds_elapsed))
    logging.info('# of requests: {:,}'.format(num_of_requests))
    logging.info('Rate: {:.2f}/s'.format(rate_of_requests))
    logging.info('')

    fraction_of_new_requests = num_of_new_requests / num_of_requests
    rate_of_new_requests = num_of_new_requests / seconds_elapsed
    logging.info('# of new requests: {:,}'.format(num_of_new_requests))
    logging.info('Fraction of all requests: {:.3f}'.\
                 format(fraction_of_new_requests))
    logging.info('Rate: {:.2f}/s'.format(rate_of_new_requests))
    logging.info('')

    percent_of_package_requests = \
      (num_of_package_requests / num_of_requests) * 100
    rate_of_package_requests = num_of_package_requests / seconds_elapsed
    logging.info('# of package requests: {:,}'.format(num_of_package_requests))
    logging.info('Percentage of all requests: {:.2f}%'.\
          format(percent_of_package_requests))
    logging.info('Rate: {:.2f}/s'.format(rate_of_package_requests))
    logging.info('')

    # number of times a number of requests is seen
    for ip_address, ip_address_count in self.ip_address_requests.items():
      num_of_num_of_requests[ip_address_count] += 1
    logging.info('[(# of requests, # of times)]: {}'.\
                 format(num_of_num_of_requests))
    logging.info('')

    num_of_users_who_request_unpopular_projects = 0

    # number of times a number of projects is seen
    for ip_address, project_names in self.ip_address_projects.items():
      project_names_count = len(project_names)
      num_of_num_of_projects[project_names_count] += 1

      if len(project_names - pop_package_names) > 0:
        num_of_users_who_request_unpopular_projects += 1

    logging.info('[(# of projects, # of times)]: {}'.\
                 format(num_of_num_of_projects))
    logging.info('# of users who request unpopular projects: {0}'.\
          format(num_of_users_who_request_unpopular_projects))
    logging.info('')

    percent_of_pop_package_requests = \
      (num_of_pop_package_requests / num_of_package_requests) * 100
    logging.info('Top {} projects for package requests: {}'.\
          format(max_rank, pop_package_requests))
    logging.info('Percentage of all package requests: {:.2f}%'.\
          format(percent_of_pop_package_requests))
    logging.info('')

    # plots
    self.plot_cumulative_request_curve(max_rank,
                                       num_of_pop_package_requests_by_rank,
                                       num_of_package_requests)
    # clear the current figure
    matplotlib.pyplot.clf()
    self.plot_cumulative_client_curve(max_rank, num_of_num_of_requests)


if __name__ == '__main__':
  # rw for owner and group but not others
  os.umask(0o07)

  logging.basicConfig(filename='/var/experiments-output/pypi-log-reader.log',
                      level=logging.DEBUG, filemode='a',
                      format='[%(asctime)s UTC] [%(name)s] [%(levelname)s] '\
                             '[%(funcName)s:%(lineno)s@%(filename)s] '\
                             '%(message)s')

  sorted_simple_log_filepath = \
    '/var/experiments-output/simple/sorted.simple.log.xz'
  try:
    sorted_simple_pypi_log_reader = SortedSimplePyPILogReader()
    sorted_simple_pypi_log_reader.parse(sorted_simple_log_filepath)
    sorted_simple_pypi_log_reader.summarize()
  except:
    logging.exception('BAM!')


