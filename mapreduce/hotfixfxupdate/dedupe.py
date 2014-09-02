import ujson as json

def map(k, d, v, cx, filename, line_num):
    cx.write(k, (d[0], filename, line_num))

def reduce(k, v, cx):
    if len(v) < 2:
        return

    v = sorted(v)
    for t in v[0:-1]:
        cx.write(k, '\t'.join([str(s) for s in t]))
