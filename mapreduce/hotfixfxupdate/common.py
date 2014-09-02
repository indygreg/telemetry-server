# This file is a module providing common code used by analysis
# scripts.

from collections import Counter
import re

NOTIFICATION_BUCKETS = [
    0,
    1,
    2,
    3,
    4,
    5,
    6,
    7,
    8,
    9,
    10,
    15,
    20,
    25,
    30,
    50,
    100,
    float('inf'),
]

DOWNLOAD_RESUME_BUCKETS = [
    0,
    1,
    2,
    3,
    4,
    5,
    10,
    15,
    20,
    30,
    40,
    50,
    100,
    float('inf'),
]

DOWNLOAD_ATTEMPT_BUCKETS = [
    0,
    1,
    2,
    3,
    4,
    5,
    10,
    15,
    20,
    30,
    40,
    50,
    100,
    float('inf'),
]

DOWNLOAD_HASH_FAILURE_BUCKETS = [
    0,
    1,
    float('inf'),
]

DOWNLOAD_COMPLETE_BUCKETS = [
    0,
    1,
    2,
    5,
    10,
    20,
    float('inf'),
]

DOWNLOAD_FAILURE_BUCKETS = [
    0,
    1,
    2,
    5,
    10,
    float('inf'),
]

DOWNLOAD_SIZE_MISMATCH_BUCKETS = [
    0,
    1,
    2,
    5,
    10,
    float('inf'),
]

DOWNLOAD_SUCCESS_BUCKETS = [
    0,
    1,
    2,
    float('inf'),
]

INSTALL_ATTEMPT_BUCKETS = [
    0,
    1,
    2,
    3,
    4,
    5,
    10,
    20,
    50,
    float('inf'),
]

INSTALL_FAILURE_BUCKETS = [
    0,
    1,
    2,
    3,
    4,
    5,
    10,
    20,
    50,
    float('inf'),
]

INSTALL_SUCCESS_BUCKETS = [
    0,
    1,
    float('inf'),
]

INSTALL_LAUNCHER_FAILURES_BUCKETS = [
    0,
    float('inf'),
]

def read_data(fh):
    data = {}

    for line in fh:
        line = line.strip()
        key, value = line.split('\t', 1)

        fields = key.split('.')
        if re.match('20\d{2}[01][0-9]{3}', fields[-1]):
            date = fields[-1]
            key = '.'.join(fields[:-1])
        else:
            date = 'all'

        try:
            major, minor = key.split('.', 1)
        except ValueError:
            major = key
            minor = ''

        try:
            minor = int(minor)
        except ValueError:
            pass

        # TODO handle windows version specific data
        if major == 'windowsVer':
            continue

        data[(major, minor, date)] = int(value)

    return data

def normalize_data(data):
    normalized = {}
    counts = Counter()

    histos = {
        'notificationsShown': NOTIFICATION_BUCKETS,
        'notificationsRemoved': NOTIFICATION_BUCKETS,
        'notificationsClicked': NOTIFICATION_BUCKETS,
        'downloadAttempts': DOWNLOAD_ATTEMPT_BUCKETS,
        'downloadResumes': DOWNLOAD_RESUME_BUCKETS,
        'downloadComplete': DOWNLOAD_COMPLETE_BUCKETS,
        'downloadHashFailure': DOWNLOAD_HASH_FAILURE_BUCKETS,
        'downloadFailures': DOWNLOAD_FAILURE_BUCKETS,
        'downloadSizeMismatch': DOWNLOAD_SIZE_MISMATCH_BUCKETS,
        'downloadSuccess': DOWNLOAD_SUCCESS_BUCKETS,
        'installAttempts': INSTALL_ATTEMPT_BUCKETS,
        'installFailures': INSTALL_FAILURE_BUCKETS,
        'installSuccesses': INSTALL_SUCCESS_BUCKETS,
        'installLauncherFailures': INSTALL_LAUNCHER_FAILURES_BUCKETS,
    }

    for (major, minor, date), value in data.items():
        if major in histos:
            for bucket in histos[major]:
                if minor <= bucket:
                    counts[(major, bucket, date)] += value
                    break

            continue

        if major == 'upgradedFrom':
            major_version = minor.split('.')[0]
            counts[(major, major_version, date)] += value
            continue

        if major == 'version':
            version = minor.split('.')[0]
            counts[(major, version, date)] += value
            continue

        normalized[(major, minor, date)] = value

    normalized.update(counts)

    return normalized

