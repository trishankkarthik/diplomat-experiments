#!/usr/bin/env python3

'''
A little script to anonymize IP addresses in log files.
'''


# 1st-party
import gzip
import hashlib
import lzma
import mimetypes
import os
import sys


# Fixed-length columns on each line must be delimited by this string.
DELIMITER = ' '

# Random fixed-salt we never store anywhere
SALT = os.urandom(256)


def anonymize(message):
  # http://stackoverflow.com/a/7585378
  encoded_messsage = message.encode('utf-8')
  return hashlib.sha256(SALT + encoded_messsage).hexdigest()


if __name__ == '__main__':
  # USAGE: python3 anonymizer.py IP_FIELD_INDEX IN1-.LOG IN-2.LOG ... IN-N.LOG
  assert len(sys.argv) >= 3
  ip_field_index = int(sys.argv[1])
  filepaths = sys.argv[2:]

  assert ip_field_index >= 0

  # rw for owner and group but not others
  os.umask(007)

  for filepath in filepaths:
    filepath_type, filepath_encoding = mimetypes.guess_type(filepath)
    anonymized_compressed_filepath = 'anonymized.' + filepath + '.xz'

    if filepath_encoding == 'gzip':
      filepath_open = gzip.open

    else:
      filepath_open = open

    with filepath_open(filepath, 'rt') as file_in, \
         lzma.open(anonymized_compressed_filepath, 'w') as file_out:
      for line in file_in:
        tokens = line.split(DELIMITER)
        tokens[ip_field_index] = anonymize(tokens[ip_field_index])
        replaced_line = DELIMITER.join(tokens)
        # http://stackoverflow.com/a/5471351
        replaced_line_as_bytes = bytes(replaced_line, 'utf-8')
        file_out.write(replaced_line_as_bytes)

    print('W ' + anonymized_compressed_filepath)
