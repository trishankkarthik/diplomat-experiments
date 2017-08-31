#!/bin/bash

umask 007

cd /var/experiments-output/anonymized/

for log in simple.*.log
do
  # Sort by timestamp (k1), IP (k2), user-agent (k4), URL (k3).
  time sort --field-separator=, --unique -k1 -k2 -k4 -k3 $log > sorted.$log
  echo sorted.$log
done

rm simple.*.log
echo 'rm simple.*.log'

time sort --field-separator=, --unique -k1 -k2 -k4 -k3 -ms -o sorted.simple.log sorted.simple.*.log
echo sorted.simple.log

# NOTE: Fixing it post festum.
# time xzcat simple/sorted.simple.log.xz | awk -F"," '{print $1, $2, $4, $3}' OFS="," | uniq | awk -F"," '{print $1, $2, $4, $3}' OFS="," | xz > simple/sorted.uniq.simple.log.xz

rm sorted.simple.*.log
echo 'rm sorted.simple.*.log'

time xz -f sorted.simple.log
echo 'xz sorted.simple.log'

mkdir /var/experiments-output/simple/
mv sorted.simple.log.xz /var/experiments-output/simple/

