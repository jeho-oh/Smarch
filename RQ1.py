import os
import pycosat
import math
import random
from scipy import stats

from smarch_mp import master
from smarch_basic import sample

srcdir = os.path.dirname(os.path.abspath(__file__))
SHARPSAT = srcdir + '/sharpSAT/Release/sharpSAT'
MARCH = srcdir + '/CnC/march_cu/march_cu'


def read_dimacs(dimacsfile_):
    """parse variables and clauses from a dimacs file"""

    _features = list()
    _clauses = list()
    _vcount = '-1'  # required for variables without names

    with open(dimacsfile_) as df:
        for _line in df:
            # read variables in comments
            if _line.startswith("c"):
                _line = _line[0:len(_line) - 1]
                _feature = _line.split(" ", 4)
                del _feature[0]
                _feature[0] = int(_feature[0])
                _features.append(tuple(_feature))

            # read dimacs properties
            elif _line.startswith("p"):
                info = _line.split()
                _vcount = info[2]

            # read clauses
            else:
                info = _line.split()
                if len(info) != 0:
                    _clauses.append(list(map(int, info[:len(info)-1])))

    return _features, _clauses, _vcount


def checksat(dimacs_, constraints_):
    """check satisfiability of given formula with constraints"""
    _features, _clauses, _vcount = read_dimacs(dimacs_)
    cnf = _clauses + constraints_
    _sol = pycosat.solve(cnf)

    if _sol == 'UNSAT':
        return False
    else:
        return True


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


def compare_dist(target_, sampleset_, statfile_):
    _ratiofile = os.path.dirname(os.path.realpath(__file__)) + "/Ratios/" + target_ + ".ratio"

    _tal = list()
    _tsl = list()
    _oal = list()
    _osl = list()

    _n = len(sampleset_[0])

    i = 1
    if os.path.exists(_ratiofile):
        with open(_ratiofile, 'r') as _rf:
            for line in _rf:
                _tr = float(line)

                _tavg = _tr * _n
                _tvar = _n * _tr * (1 - _tr)
                _tstd = math.sqrt(_tvar)

                _tal.append(_tavg)
                _tsl.append(_tstd)

                obs = list()

                for _samples in sampleset_:
                    _hit = 0

                    for s in _samples:
                        if (str(i) in s) or (i in s):
                            _hit += 1

                    obs.append(_hit)

                _oavg = stats.tmean(obs)
                _ostd = stats.tstd(obs)

                _oal.append(_oavg)
                _osl.append(_ostd)

                i += 1

        sf = open(statfile_, 'w')
        for i in range(0, len(_tal)):
            sf.write(str(i) + "," + str(_tal[i]) + "," + str(_tsl[i]) + str(_oal[i]) + "," + str(_osl[i]) + "\n")

        taa = stats.tmean(_tal)
        tsa = stats.tmean(_tsl)
        oaa = stats.tmean(_oal)
        osa = stats.tmean(_osl)

        print("AVG:" + str(taa) + "," + str(tsa) + "," + str(oaa) + "," + str(osa))
        sf.write("AVG:" + str(taa) + "," + str(tsa) + "," + str(oaa) + "," + str(osa))
        sf.close()


def compare_dist_smarch_opt(target_, n_, i_):
    _dimacs = root + "/FeatureModel/" + target + ".dimacs"

    _sampleset = list()

    for i in range(0, i_):
        print(i, end=',', flush=True)

        samplefile_ = root + "/Samples/RQ1/" + target_ + "/opt_" + str(n_) + "_" + str(i) + ".samples"

        features, clauses, vcount = read_dimacs(_dimacs)
        _samples = master(vcount, clauses, n_, sdir, [], 7, True)

        of = open(samplefile_, 'w')
        for s in _samples:
            for v in s:
                of.write(str(v))
                of.write(",")
            of.write("\n")
        of.close()

        _sampleset.append(_samples)
    print()

    _statfile = root + "/Samples/RQ1/" + target_ + "/opt_500.stats"
    compare_dist(target_, _sampleset, _statfile)

    _subsamplelist = list()
    for samples in _sampleset:
        _rands = get_random(300, 500)
        _subsamples = list()

        for r in _rands:
            _subsamples.append(samples[r-1])
        _subsamplelist.append(_subsamples)

    _statfile = root + "/Samples/RQ1/" + target_ + "/opt_300.stats"
    compare_dist(target_, _subsamplelist, _statfile)

    _subsamplelist = list()
    for samples in _sampleset:
        _rands = get_random(100, 500)
        _subsamples = list()

        for r in _rands:
            _subsamples.append(samples[r-1])
        _subsamplelist.append(_subsamples)

    _statfile = root + "/Samples/RQ1/" + target_ + "/opt_100.stats"
    compare_dist(target_, _subsamplelist, _statfile)

    return


def compare_dist_smarch_base(target_, n_, i_):
    _dimacs = root + "/FeatureModel/" + target + ".dimacs"

    _wdir = root + "/Samples/RQ1/" + target_ + "/smarch"
    if not os.path.exists(_wdir):
        os.makedirs(_wdir)

    _sampleset = list()

    for i in range(0, i_):
        print(i, end=',', flush=True)

        samplefile_ = root + "/Samples/RQ1/" + target_ + "/base_" + str(n_) + "_" + str(i) + ".samples"

        features, clauses, vcount = read_dimacs(_dimacs)
        _samples = sample(vcount, clauses, n_, _wdir, [], True)

        of = open(samplefile_, 'w')
        for s in _samples:
            for v in s:
                of.write(str(v))
                of.write(",")
            of.write("\n")
        of.close()

        _sampleset.append(_samples)
    print()

    _statfile = root + "/Samples/RQ1/" + target_ + "/opt_500.stats"
    compare_dist(target_, _sampleset, _statfile)

    _subsamplelist = list()
    _rands = get_random(300, 500)
    for samples in _sampleset:
        _subsamples = list()
        for r in _rands:
            _subsamples.append(samples[r])
        _subsamplelist.append(_subsamples)

    _statfile = root + "/Samples/RQ1/" + target_ + "/opt_300.stats"
    compare_dist(target_, _sampleset, _statfile)

    _subsamplelist = list()
    _rands = get_random(100, 500)
    for samples in _sampleset:
        _subsamples = list()
        for r in _rands:
            _subsamples.append(samples[r])
        _subsamplelist.append(_subsamples)

    _statfile = root + "/Samples/RQ1/" + target_ + "/opt_100.stats"
    compare_dist(target_, _sampleset, _statfile)


if __name__ == "__main__":
    root = os.path.dirname(os.path.realpath(__file__))

    targets = ("lrzip","LLVM","X264","Dune","BerkeleyDBC","HiPAcc","JHipster","Polly","7z","JavaGC","VP9",
               "fiasco_17_10","axtls_2_1_4","fiasco","toybox","axTLS","uClibc-ng_1_0_29","toybox_0_7_5",
               "uClinux","ref4955","adderII","ecos-icse11","m5272c3","pati","olpce2294",
               "integrator_arm9","at91sam7sek","se77x9","phycore229x","busybox-1.18.0","busybox_1_28_0",
               "embtoolkit","freebsd-icse11","uClinux-config","buildroot","freetz","2.6.28.6-icse11",
               "2.6.32-2var","2.6.33.3-2var")

    for target in ("pati",):
        sdir = root + "/Samples/RQ1/" + target
        if not os.path.exists(sdir):
            os.makedirs(sdir)

        # for n in (500,):
        #     print("base", end=',')
        #     compare_dist_smarch_base(target, n, 20)

        for n in (500,):
            print("opt", end=',')
            compare_dist_smarch_opt(target, n, 20)


