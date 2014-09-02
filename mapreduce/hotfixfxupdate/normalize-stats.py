#!/usr/bin/env python

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from common import (
    normalize_data,
    read_data,
)

with open(sys.argv[1], 'rb') as fh:
    data = read_data(fh)
    data = normalize_data(data)

for (major, minor, date), value in sorted(data.items()):
    print('%s\t%s\t%s\t%s' % (major, minor, date, value))
