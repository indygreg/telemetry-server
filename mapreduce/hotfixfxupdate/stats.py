import ujson as json

import datetime

STATE_KEYS = [
    'downloadAttempts',
    'downloadFailures',
    'installAttempts',
    'installFailures',
    'installLauncherFailures',
    'installSuccesses',
    #'lastNotifyDay',
    'notificationsClicked',
    'notificationsDismissed',
    'notificationsRemoved',
    'notificationsShown',
    'uninstallReason',
    'upgradedFrom',
]

downloadSpeedBuckets = [
      10000,
      25000,
      50000,
      75000,
     100000,
     150000,
     200000,
     250000,
     300000,
     350000,
     400000,
     450000,
     500000,
     600000,
     700000,
     800000,
     900000,
    1000000,
    1250000,
    1500000,
    1750000,
    2000000,
    3000000,
    4000000,
    5000000,
    float('inf'),
]

oldrecords = {}

with open('oldrecords', 'rb') as fh:
    for line in fh:
        line = line.strip()
        uid, date, filename, offset = line.split()
        offset = int(offset)
        oldrecords.setdefault(filename, set()).add(offset)

def map(k, d, v, cx, filename, line_num):
    date = d[0]
    cx.write('count.all', 1)
    cx.write('count.all.%s' % date, 1)

    if line_num in oldrecords.get(filename, set()):
        cx.write('dedupe', 1)
        return

    try:
        j = json.loads(v)
        state = j.get('state', {})

        cx.write('count', 1)
        cx.write('count.processed.%s' % date, 1)

        actualWinVer = tuple(state.get('actualWindowsVersion', [None, None, None]))
        reportedWinVer = tuple(state.get('reportedWindowsVersion', [None, None, None]))

        if actualWinVer[0] == 5 and actualWinVer[1] == 1:
            reportWinVer = 'xp'
        elif actualWinVer[0] == 6 and actualWinVer[1] == 0:
            reportWinVer = 'vista'
        elif actualWinVer[0] == 6 and actualWinVer[1] == 1:
            reportWinVer = '7'
        elif reportedWinVer[0] == 6 and reportedWinVer[1] == 2:
            reportWinVer == '8'
        elif reportedWinVer[0] >= 6:
            reportWinVer = '8.1+'
        else:
            reportWinVer = 'old'

        cx.write('channel.%s' % j.get('channel', 'UNKNOWN'), 1)
        cx.write('locale.%s' % j.get('locale', 'UNKNOWN'), 1)
        cx.write('os.%s' % j.get('os', 'UNKNOWN'), 1)
        cx.write('partner.%s' % j.get('partner', 'UNKNOWN'), 1)
        cx.write('updateAuto.%s' % j.get('updateAuto', 'UNKNOWN'), 1)
        cx.write('updateEnabled.%s' % j.get('updateEnabled', 'UNKNOWN'), 1)
        cx.write('version.%s' % j.get('version', 'UNKNOWN'), 1)

        for k in STATE_KEYS:
            v = state.get(k, 'UNKNOWN')
            cx.write('%s.%s' % (k, v), 1)
            cx.write('%s.%s.%s' % (k, v, date), 1)
            cx.write('windowsVer.%s.%s.%s' % (k, v, reportWinVer), 1)


        normalized = [str(a) for a in reportedWinVer]
        cx.write('windowsVersion.%s' % '.'.join(normalized), 1)
        cx.write('windowsVersionSubset.count.%s' % reportWinVer, 1)


        if actualWinVer > reportedWinVer:
            cx.write('compatMode.enabled', 1)
        else:
            cx.write('compatMode.disabled', 1)

        for k, v in state.get('launcherExitCodes', {}).items():
            cx.write('exitCode.%s' % k, v)
            cx.write('exitCode.%s.%s' % (k, date), v)
            cx.write('windowsVer.exitCode.%s.%s' % (k, reportWinVer), v)

        downloadSuccess = 0
        downloadComplete = 0
        downloadSizeMismatch = 0
        downloadHashFailure = 0
        downloadResumes = 0
        fhr_tags = set()
        lastDownloadProgress = None
        lastLogWasDownload = False
        downloadSpeeds = []
        log = j.get('logHotfix', [])
        if log is None:
            log = []

        first_day = '0000-00-00'
        try:
            time = log[0][0] / 1000
            dt = datetime.datetime.utcfromtimestamp(time)
            first_day = dt.date().isoformat()
        except IndexError:
            pass

        last_day = '0000-00-00'
        try:
            time = log[-1][0] / 1000
            dt = datetime.datetime.utcfromtimestamp(time)
            last_day = dt.date().isoformat()
        except IndexError:
            pass

        cx.write('firstLogDay.%s' % first_day, 1)
        cx.write('lastLogDay.%s' % last_day, 1)

        for time, priority, message in log:
            isDownload = False

            if message == 'Moved installer to final location.':
                downloadSuccess += 1
            elif message == 'Verifying download.':
                downloadComplete += 1
            elif message.startswith('File size does not match:'):
                downloadSizeMismatch += 1
            elif message == 'File hash mismatch!':
                downloadHashFailure += 1
            elif message.startswith('Resuming download at'):
                downloadResumes += 1
            elif message == 'FHR not present.':
                fhr_tags.add('not_present')
            elif message == 'FHR policy not present.':
                fhr_tags.add('no_policy')
            elif message == 'User has responded to FHR policy.':
                fhr_tags.add('active')
            elif message == 'User hasn\'t responded to FHR policy. Shutting down.':
                fhr_tags.add('no_policy_response')
            elif message.startswith('Error interacting with FHR policy:'):
                fhr_tags.add('policy_error')
            elif message == 'Could not initialize FHR. Weird.':
                fhr_tags.add('init_error')
            elif message.startswith('Exception interacting with FHR: '):
                fhr_tags.add('exception')
            elif message.startswith('Download progress: '):
                isDownload = True

                s = message[len('Download progress: '):]
                completed, total = s.strip().split('/')
                try:
                    completed = int(completed)
                    total = int(total)
                # A very small amount of logs have "NaN".
                except ValueError:
                    lastLogWasDownload = False
                    continue

                if lastLogWasDownload:
                    delta_time = time - lastDownloadProgress[0]
                    # If time didn't change, something funky happend. Ignore
                    # it.
                    if delta_time:
                        # Milliseconds to seconds.
                        delta_time = delta_time / 1000.0
                        delta_size = completed - lastDownloadProgress[1]
                        downloadSpeeds.append(
                            float(delta_size) / float(delta_time))

                lastDownloadProgress = (time, completed)

            lastLogWasDownload = isDownload

        cx.write('downloadComplete.%d' % downloadComplete, 1)
        cx.write('downloadSizeMismatch.%d' % downloadSizeMismatch, 1)
        cx.write('downloadHashFailure.%d' % downloadHashFailure, 1)
        cx.write('downloadSuccess.%d' % downloadSuccess, 1)
        cx.write('downloadResumes.%d' % downloadResumes, 1)

        for tag in fhr_tags:
            cx.write('fhr.%s' % tag, 1)

        if downloadSpeeds:
            mean = sum(downloadSpeeds) / float(len(downloadSpeeds))

            for bucket in downloadSpeedBuckets:
                if mean <= bucket:
                    cx.write('downloadMean.%s' % bucket, 1)
                    cx.write('downloadMean.%s.%s' % (bucket, date), 1)
                    break

    except Exception as e:
        import traceback
        traceback.print_exc()
        cx.write("ERROR.%s" % str(e), 1)

def reduce(k, v, cx):
    try:
        k = str(k)
    except UnicodeEncodeError:
        k = k.encode('utf-8', 'replace')

    cx.write(k, sum(v))
