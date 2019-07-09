import os
from subprocess import getoutput
import random
import pycosat

from smarch_mp import master
from smarch_basic import sample

srcdir = os.path.dirname(os.path.abspath(__file__))
SHARPSAT = srcdir + '/sharpSAT/Release/sharpSAT'


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


def gen_dimacs(vars_, clauses_, constraints_, outfile_):
    """generate a dimacs file from given clauses and constraints"""

    _df = open(outfile_, 'w')
    _df.write('p cnf ' + vars_ + ' ' + str(len(clauses_) + len(constraints_)) + '\n')

    for cl in clauses_:
        _df.write(" ".join(str(x) for x in cl) + ' 0 \n')

    for ct in constraints_:
        if isinstance(ct, (list,)):
            _line = ""
            for _v in ct:
                _line = _line + str(_v) + " "
            _df.write(_line + '0 \n')
        else:
            _df.write(str(ct) + ' 0 \n')

    _df.close()


def count(dimacs_, constraints_):
    """count dimacs solutions with given constraints"""

    _tempdimacs = os.path.dirname(dimacs_) + '/count.dimacs'
    _features, _clauses, _vcount = read_dimacs(dimacs_)

    gen_dimacs(_vcount, _clauses, constraints_, _tempdimacs)
    res = int(getoutput(SHARPSAT + ' -q ' + _tempdimacs))

    return res


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


def compute_error(dimacs_, samples_):
    features, clauses, vcount = read_dimacs(dimacs)

    total = count(dimacs_, [])

    avg = 0
    i = 0

    for f in features:
        fv = [f[0]]

        # print(f, end=":")

        if checksat(dimacs_, [fv]):
            tp = count(dimacs_, [fv])
            tr = tp/total

            hit = 0
            for s in samples_:
                if fv[0] in s:
                    hit += 1

            sr = hit / len(samples_)

            error = abs(sr-tr)
            # print(error)
            i += 1
            avg += error

    # print("Average: " + str(avg / i))
    return avg / i


def get_error_smarch_basic(dimacs_, samplefile_, n_):
    wdir = os.path.dirname(dimacs) + "/smarch"
    if not os.path.exists(wdir):
        os.makedirs(wdir)

    features, clauses, vcount = read_dimacs(dimacs)
    _samples = sample(vcount, clauses, n_, wdir, [], True)

    of = open(samplefile_, 'w')
    for s in _samples:
        for v in s:
            of.write(str(v))
            of.write(",")
        of.write("\n")
    of.close()

    return compute_error(dimacs_, _samples)


def get_error_smarch_mp(dimacs_, samplefile_, n_,):
    wdir = os.path.dirname(dimacs) + "/smarch"
    if not os.path.exists(wdir):
        os.makedirs(wdir)

    features, clauses, vcount = read_dimacs(dimacs)
    _samples = master(vcount, clauses, n_, wdir, [], 7, True)

    of = open(samplefile_, 'w')
    for s in _samples:
        for v in s:
            of.write(str(v))
            of.write(",")
        of.write("\n")
    of.close()

    return compute_error(dimacs_, _samples)


def get_error_enum(dimacs_, enumfile_, samplefile_, n_):
    _configs = list()
    with open(enumfile_, 'r') as f:
        for line in f:
            config = line.split(',')
            config = config[0:len(config)-1]
            config = list(map(int, config))

            _configs.append(config)

    _rands = get_random(n_, len(_configs))

    _samples = list()
    for r in _rands:
        _samples.append(_configs[r-1])

    of = open(samplefile_, 'w')
    for s in _samples:
        for v in s:
            of.write(str(v))
            of.write(",")
        of.write("\n")
    of.close()

    return compute_error(dimacs_, _samples)


# target = "Dune"
# n = 300
rep = 25


for target in ("Apache",): #("BerkeleyDBC", "HSMGP", "HiPAcc", "Trimesh", "JHipster"):
    print(target)

    dimacs = os.path.dirname(os.path.realpath(__file__)) + "/FeatureModel/" + target + ".dimacs"

    rdir = os.path.dirname(os.path.realpath(__file__)) + "/Samples/RQ1/" + target
    if not os.path.exists(rdir):
        os.makedirs(rdir)

    for n in (300,):
        print(n)
        bavg = 0
        oavg = 0
        eavg = 0

        resfile = rdir + "/" + target + "_" + str(n) + ".out"
        rf = open(resfile, 'w')
        rf.write("iter,basic,opt,enum\n")
        print("iter,basic,opt,enum")

        for i in range(0, rep):
            rf.write(str(i) + ",")
            print(str(i), end=",")

            samplefile = rdir + "/basic_" + str(n) + "_" + str(i) + ".samples"
            berror = get_error_smarch_basic(dimacs, samplefile, n)
            print(berror, end=",")
            rf.write(str(berror) + ",")
            bavg += berror

            samplefile = rdir + "/opt_" + str(n) + "_" + str(i) + ".samples"
            oerror = get_error_smarch_mp(dimacs, samplefile, n)
            print(oerror, end=",")
            rf.write(str(oerror) + ",")
            oavg += oerror

            enumfile = os.path.dirname(os.path.realpath(__file__)) + "/Samples/enumeration/" + target + ".samples"
            samplefile = rdir + "/enum_" + str(n) + "_" + str(i) + ".samples"
            eerror = get_error_enum(dimacs, enumfile, samplefile, n)
            print(eerror)
            rf.write(str(eerror) + "\n")
            eavg += eerror

        bavg = bavg / rep
        print(bavg, end=",")
        oavg = oavg / rep
        print(oavg, end=",")
        eavg = eavg / rep
        print(eavg)

        rf.write("avg,")
        rf.write(str(bavg) + ",")
        rf.write(str(oavg) + ",")
        rf.write(str(eavg) + "\n")

        rf.close()

