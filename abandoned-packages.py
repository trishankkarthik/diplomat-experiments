#!/usr/bin/env python3


# 1st-party
import json

# 3rd-party
import matplotlib
# Force matplotlib to not use any Xwindows backend.
# http://stackoverflow.com/a/3054314
matplotlib.use('Agg')
import matplotlib.pyplot as pyplot
import numpy


PACKAGE_TIMESTAMPS_FILENAME = '/var/experiments-output/package_cache.json'

# The experiment is only valid since the following Unix timestamp.
SINCE_TIMESTAMP = 1395360000

# For every project, we get list of timestamps (sorted in increasing order)
# that the project added/updated/removed some package.
# {
#   "Django": [timestamp("May 17 2010"), ..., timestamp("Oct 22 2014")]
# }
with open(PACKAGE_TIMESTAMPS_FILENAME) as package_timestamps_json:
  project_timestamps = json.load(package_timestamps_json)

# For every project, what is the largest time gap between any two consecutive
# package updates? In other words, if the project has the package update
# timestamps [t1, t2, ..., tn], then we want max(t_{i+1}-t_i),
# where 1 <= i < n. A project will have the max time gap only if there were at
# least two package updates; otherwise the project will have no entry.
project_max_update_time_gap = {}

# How many projects were mostly updated since the compromise?
num_of_projects_with_only_one_update_before_compromise = 0
num_of_projects_with_no_update_before_compromise = 0

# Compute these max time gaps.
for project, timestamps in project_timestamps.items():
  sorted_timestamps = sorted(timestamps)

  # Seems reasonable to consider timestamps only before the compromise, because
  # PyPI must have made decisions to claim based on these timestamps before the
  # compromise.
  sorted_timestamps_before_compromise = [timestamp \
                                         for timestamp \
                                         in sorted_timestamps \
                                         if timestamp < SINCE_TIMESTAMP]

  if len(sorted_timestamps_before_compromise) == 0:
    num_of_projects_with_no_update_before_compromise += 1

  elif len(sorted_timestamps_before_compromise) == 1:
    num_of_projects_with_only_one_update_before_compromise +=1
    # Consider the update time gap to be nothing.
    project_max_update_time_gap[project] = 0

  else:
    max_time_gap = 0

    # TODO: what if there was no timestamp?
    # TODO: what if there was only one timestamp?
    for i in range(len(sorted_timestamps_before_compromise)-1):
      curr_timestamp = sorted_timestamps_before_compromise[i]
      next_timestamp = sorted_timestamps_before_compromise[i+1]

      assert curr_timestamp > 0
      assert curr_timestamp < SINCE_TIMESTAMP

      assert next_timestamp > 0
      assert next_timestamp < SINCE_TIMESTAMP

      time_gap = next_timestamp - curr_timestamp
      assert time_gap > 0
      max_time_gap = max(time_gap, max_time_gap)

    # Set the max update time gap for this project.
    project_max_update_time_gap[project] = max_time_gap

# How many projects have a package update time gap before the compromise?
num_of_projects = len(project_timestamps)
num_of_projects_with_max_time_gap = len(project_max_update_time_gap)
assert num_of_projects_with_max_time_gap <= num_of_projects

# NOTE: < 50% of known projects have a time gap before compromise...
print('# of projects with a max update time gap before compromise: {:,}'\
      .format(num_of_projects_with_max_time_gap))
print('# of projects with no update before compromise: {:,}'\
      .format(num_of_projects_with_no_update_before_compromise))
print('# of projects with only one update before compromise: {:,}'\
      .format(num_of_projects_with_only_one_update_before_compromise))
print('# of projects: {:,}'.format(num_of_projects))

# Plot CDF of the projects' max update time gaps.
# NOTE: Try 1-year gap for 10 years.
years = 5
months_in_a_year = 12
seconds_in_a_month = 30*24*60*60
months = range(0, months_in_a_year*years)
gaps_in_seconds = [seconds_in_a_month*i for i in months] 
max_update_time_gap_cdf = []

for this_update_time_gap in gaps_in_seconds:
  # How many projects have a time gap at least as big as this one?
  leq_time_gaps = [
      that_update_time_gap \
      for that_update_time_gap \
      in project_max_update_time_gap.values() \
      if that_update_time_gap <= this_update_time_gap
  ]

  for that_update_time_gap in leq_time_gaps:
    assert that_update_time_gap <= this_update_time_gap

  assert len(leq_time_gaps) <= num_of_projects
  cumulative_probability = len(leq_time_gaps)/num_of_projects_with_max_time_gap
  assert cumulative_probability <= 1
  max_update_time_gap_cdf.append(cumulative_probability)

# Draw the CDF.
assert len(gaps_in_seconds) == len(max_update_time_gap_cdf)
print(max_update_time_gap_cdf)

INDICES = numpy.arange(len(max_update_time_gap_cdf))
print(INDICES)
pyplot.plot(INDICES, max_update_time_gap_cdf, 'r--')

# add title, labels, ticks, legends
pyplot.title('CDF of the max difference in update time')

pyplot.xlabel('Max difference in update time (in months)')
#xlabels = [str(+1) for i in months]
#pyplot.xticklabels(xlabels)
step_months = range(0, months_in_a_year*years, 5)
pyplot.xticks(step_months, [str(m) for m in step_months])
pyplot.xlim([-1, months[-1]+.01])

pyplot.ylabel('Cumulative fraction of projects')
pyplot.ylim([-0.01, 1.01])

# write the actual plot
pyplot.savefig('/var/experiments-output/abandoned-projects-cdf.png')


