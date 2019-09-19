import os
import random
import math
from scipy import stats

root = os.path.dirname(os.path.realpath(__file__))

def estimate_error(tr_, n_):
    est = 0

    for i in range(0, n_+1):
        pr = stats.binom.pmf(i, n_, tr_)
        est += abs((i / n_) - tr_) * pr

    return est


def compute_error(target_, samples_, statfile_):
    _ratiofile = root + "/Ratios/" + target_ + ".ratio"

    trs = list()
    srs = list()

    eavg = 0
    mecount = 0
    esterr = 0

    _n = len(samples_)
    i = 1
    if os.path.exists(_ratiofile):
        with open(_ratiofile, 'r') as _rf:
            for line in _rf:
                tr = float(line)
                se = math.sqrt((tr * (1-tr)) / _n)
                me = se * 1.96

                esterr += estimate_error(tr, _n)

                hit = 0
                for s in samples_:
                    if (str(i) in s) or (i in s):
                        hit += 1

                sr = hit / len(samples_)

                trs.append(tr)
                srs.append(sr)

                err = abs(sr - tr)
                eavg += err

                if err <= me:
                    mecount += 1

                i += 1

        mecount /= (i - 1)
        res = "Pass" if (mecount >= 0.95) else "Fail"

        print(str(_n) + "," + str(mecount) + "," + str(eavg / (i - 1)) + "," + str(esterr / (i-1)))

        sf = open(statfile_, "w")

        sf.write("Ratio within margin of error " + str(mecount) + "\n")
        sf.write("Result = " + res + "\n")
        sf.write("\n")

        sf.write("True Ratio,Estimated Ratio\n")
        for i in range(0, len(trs)):
            sf.write(str(trs[i]) + "," + str(srs[i]) + "\n")

        sf.close()


def get_error_smarch(target_, version_, n_):
    _dimacs = root + "/FeatureModel/" + target_ + ".dimacs"
    _samplefile = root + "/Samples/" + version_ + "/" + target_ + "_" + str(n_) + ".samples"

    _samples = list()
    if os.path.exists(_samplefile):
        with open(_samplefile, "r") as sf:
            for line in sf:
                raw = line.split(',')
                config = raw[:len(raw) - 1]
                _samples.append(config)
    else:
        print(target_ + " samples not found!!")
        return

    _statfile = root + "/Stats/RQ1/" + target_ + "_" + version_ + "_" + str(n_) + ".stats"
    compute_error(target_, _samples, _statfile)


if __name__ == "__main__":
    targets = ("uClibc-ng_1_0_29", "VP9", "toybox_0_7_5", "fiasco_17_10", "pati", "busybox_1_28_0")

    for target in targets:
        print(target)

        for n in (100, 500, 1000):
            get_error_smarch(target, "smarch_opt", n)

        print()
