import os
import random
import math
from scipy import stats

root = os.path.dirname(os.path.realpath(__file__))


# generate n random numbers for sampling
def get_random(rcount_, total_):
    def gen_random():
        while True:
            yield random.randrange(1, total_ + 1, 1)

    def gen_n_unique(source, n__):
        seen = set()
        seenadd = seen.add
        for i in (i for i in source() if i not in seen and not seenadd(i)):
            yield i
            if len(seen) == n__:
                break

    return [i for i in gen_n_unique(gen_random, min(rcount_, int(total_)))]


def num_features_smarch(samplefile_, n_):
    _configs = list()

    if os.path.exists(samplefile_):
        with open(samplefile_, "r") as sf:
            for line in sf:
                raw = line.split(',')
                config = raw[:len(raw) - 1]
                _configs.append(config)
    else:
        return -1

    _samples = list()
    if n_ < 0:
        _samples = _configs.copy()
    else:
        rands = get_random(n_, len(_configs))
        for r in rands:
            _samples.append(_configs[r - 1])

    _fnums = list()
    for sample in _samples:
        fnum = 0
        for v in sample:
            if not v.startswith('-'):
                fnum += 1
        _fnums.append(fnum)

    if n_ < 0:
        avg = stats.tmean(_fnums)
        std = stats.tstd(_fnums)
        return avg, std

    return stats.tmean(_fnums), stats.tstd(_fnums)


def num_features_DDbS(samplefile_, n_):
    _configs = list()
    init = True

    if os.path.exists(samplefile_):
        with open(samplefile_, 'r') as sf:
            for line in sf:
                if not init:
                    raw = line.split(";")
                    if len(raw) != 0:
                        raw = raw[1:]
                        config = list()
                        for i in range(0, len(raw)):
                            if raw[i] == '1':
                                config.append(i + 1)
                        _configs.append(config)
                else:
                    init = False
    else:
        return -1

    _fnums = list()
    for sample in _configs:
        fnum = 0
        for v in sample:
            if v > 0:
                fnum += 1
        _fnums.append(fnum)

    return stats.tmean(_fnums), stats.tstd(_fnums)


def num_features_QS(samplefile_, n_):
    i = 0

    _configs = list()
    if os.path.exists(samplefile_):
        with open(samplefile_, 'r') as sf:
            for line in sf:
                raw = line.split(" ")
                if len(raw) != 0:
                    config = raw[:len(raw) - 1]
                    _configs.append(config)
                i += 1

    else:
        return -1

    _samples = list()
    rands = get_random(n_, len(_configs))
    for r in rands:
        _samples.append(_configs[r - 1])

    _fnums = list()
    for sample in _samples:
        fnum = 0
        for v in sample:
            if not v.startswith('-'):
                fnum += 1
        _fnums.append(fnum)

    return stats.tmean(_fnums), stats.tstd(_fnums)


if __name__ == "__main__":
    targets = ("VP9", "JHipster")  # , "toybox_0_7_5", "pati", "busybox_1_28_0")
    repdir = os.path.dirname(os.path.realpath(__file__)) + "/Replication"

    for target in targets:
        print(target)

        samplefile = root + "/Samples/enumeration/" + target + ".samples"
        avg, std = num_features_smarch(samplefile, -1)

        for n in (100, 200, 300, 400, 500, 600, 700, 800, 900, 1000):
            print(str(n) + "," + str(avg), end=",")

            low = avg - (1.96 * (std / math.sqrt(n)))
            high = avg + (1.96 * (std / math.sqrt(n)))
            print(str(low), end=",")
            print(str(high), end=",")

            samplefile = repdir + "/DbS/Samples_ex/" + target + "_" + str(n) + ".csv"
            davg, dstd = num_features_DDbS(samplefile, n)

            samplefile = repdir + "/QuickSampler/Samples_ex/" + target + ".dimacs.samples.valid"
            qavg, qstd = num_features_QS(samplefile, n)

            samplefile = root + "/Samples/smarch_opt/" + target + "_1000.samples"
            savg, sstd = num_features_smarch(samplefile, n)

            print(str(davg) + "," + str(qavg) + "," + str(savg), end=",")
            print(str(dstd) + "," + str(qstd) + "," + str(sstd), end=",")
            print()

        print()
