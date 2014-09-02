#!/usr/bin/env python

# This script reads data produced from the stats.py job and formats it nicely.
# Usage: 

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from common import (
    normalize_data,
    read_data,
)

NO_CUMULATIVE = {
    'locale',
    'os',
}

IGNORE_MAJOR = {
    'count',
    'dedupe',
    'os',
    'partner',
}

with open(sys.argv[1], 'rb') as fh:
    data = normalize_data(read_data(fh))

longest_major = max(len(t[0]) for t in data)

longest_minor = {}
for (major, minor, date), v in data.items():
    longest_minor.setdefault(major, 0)

    if len(str(minor)) > longest_minor[major]:
        longest_minor[major] = len(str(minor))

total = data[('count', '', 'all')]

last_major = None
cumulative_percent = 0.0
for (major, minor, date), v in sorted(data.items()):
    if major in IGNORE_MAJOR:
        continue

    if date != 'all':
        continue

    if major != last_major:
        cumulative_percent = 0.0

    last_major = major

    percent = float(v) / float(total) * 100
    cumulative_percent += percent

    fields = [
        major.ljust(len(major) + 2),
        str(minor).rjust(longest_minor[major] + 1),
        ('%.2f%%' % percent).rjust(7),
    ]

    if major not in NO_CUMULATIVE:
        fields.append(('%.2f%%' % cumulative_percent).rjust(12))
        left = 100.0 - cumulative_percent
        fields.append(('%.2f%%' % left).rjust(12))

    print(''.join(fields))
