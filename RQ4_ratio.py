import os
from os import listdir
from os.path import isfile, join
from subprocess import getoutput
import math
import multiprocessing
import pycosat
import shutil

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


def checksat(dimacs_, constraints_):
    """check satisfiability of given formula with constraints"""
    _features, _clauses, _vcount = read_dimacs(dimacs_)
    cnf = _clauses + constraints_
    _sol = pycosat.solve(cnf)

    if _sol == 'UNSAT':
        return False
    else:
        return True


def count(dimacs_, constraints_):
    """count dimacs solutions with given constraints"""

    _tempdimacs = os.path.dirname(dimacs_) + '/count.dimacs'
    _features, _clauses, _vcount = read_dimacs(dimacs_)

    gen_dimacs(_vcount, _clauses, constraints_, _tempdimacs)
    res = int(getoutput(SHARPSAT + ' -q ' + _tempdimacs))

    return res


# partition space by cubes and count number of solutions for each cube
def count_cc(assigned_, vcount_, clauses_, wdir_, processes_):
    """ count the number of solutions with cube and conquer """
    _total = 0
    _counts = list()
    _cubes = list()
    _freevar = list()
    _dimacsfile = wdir_ + '/dimacs.smarch'
    _cubefile = wdir_ + '/cubes.smarch'

    def count_mp(q_, cubes_):
        _sol = list()

        pid = os.getpid()
        _tempdimacs = wdir_ + '/' + str(pid) + '/count.dimacs'
        if not os.path.exists(wdir_ + '/' + str(pid)):
            os.makedirs(wdir_ + '/' + str(pid))

        for cube in cubes_:
            gen_dimacs(vcount_, clauses_, cube + assigned_, _tempdimacs)
            cres = int(getoutput(SHARPSAT + ' -q ' + _tempdimacs))
            _sol.append(cres)

        q_.put([cubes_, _sol])

        shutil.rmtree(wdir_ + '/' + str(pid))

    # create dimacs file regarding constraints
    gen_dimacs(vcount_, clauses_, assigned_, _dimacsfile)

    # execute march to get cubes
    res = getoutput(MARCH + ' ' + _dimacsfile + ' -d 5 -#')
    _out = res.split("\n")

    _allfree = False

    for _line in _out:
        if _line.startswith("c free"):
            _freevar = _line.split(": ")[1].split()
        elif _line.startswith('c all'):
            _allfree = True
        elif _line.startswith('a'):
            _cube = list(_line.split())
            _cube = _cube[1:len(_cube)-1]
            _cubes.append(_cube)

    # double check all variables are free
    if _allfree:
        _total = int(getoutput(SHARPSAT + ' -q ' + _dimacsfile))
        if _total != 2 ** (len(_freevar)):
            _freevar.clear()
            _allfree = False

    if not _allfree:
        # with open(_cubefile) as cf:
        #     for _line in cf:
        #         _cube = list(_line.split())
        #         if 'a' in _cube:
        #             _cube.remove('a')
        #         if '0' in _cube:
        #             _cube.remove('0')
        #
        #         _cubes.append(_cube)

        _freevar.clear()

        # execute sharpSAT to count solutions
        # count in parallel
        if processes_ > 1:
            # partition random numbers for each thread
            chunk = math.ceil(len(_cubes) / processes_)
            pnum = math.ceil(len(_cubes) / chunk)

            clist = list()
            for i in range(0, pnum):
                clist.append(_cubes[i * chunk: (i + 1) * chunk])

            # run sampling processes
            _samples = list()
            with multiprocessing.Manager() as manager:
                q = manager.Queue()
                plist = list()

                # create processes
                for i in range(0, len(clist)):
                    plist.append(
                        multiprocessing.Process(target=count_mp,
                                                args=(q, clist[i])))

                # start processes
                for p in plist:
                    p.start()

                # wait until processes are finished
                for p in plist:
                    p.join()

                # gather samples
                _cubes.clear()
                while not q.empty():
                    pres = q.get()

                    _cubes.extend(pres[0])
                    _counts.extend(pres[1])

                for c in _counts:
                    _total += c

        # cont without parallelism
        else:
            for _cube in _cubes:
                gen_dimacs(vcount_, clauses_, assigned_ + _cube, _dimacsfile)
                res = int(getoutput(SHARPSAT + ' -q ' + _dimacsfile))
                _total += res
                _counts.append(res)

    return _freevar, _counts, _cubes, _total, _allfree


def check_combratio(dimacs_, outfile_):
    _features, _clauses, _vcount = read_dimacs(dimacs_)
    _wdir = os.path.dirname(os.path.realpath(dimacs_)) + "/smarch"
    if not os.path.exists(_wdir):
        os.makedirs(_wdir)

    # count total number of configurations
    total = count_cc([], _vcount, _clauses, _wdir, 7)[3]

    out = open(outfile_, "w")

    for i in range(1, int(_vcount)+1):
        if checksat(dimacs_, [[i]]):

            # compute ratio
            tp = count_cc([i], _vcount, _clauses, _wdir, 7)[3]
            tr = tp / total

            out.write(str(tr) + "\n")

            # print progress
            print(str(i) + ": " + str(tr))
        else:
            out.write("0\n")

            # print progress
            print(str(i) + ": 0")

    out.close()


def compute_error(dimacs_, samples_):
    features, clauses, vcount = read_dimacs(dimacs_)
    wdir = os.path.dirname(os.path.realpath(dimacs_)) + "/smarch"
    if not os.path.exists(wdir):
        os.makedirs(wdir)

    # total = count(dimacs_, [])
    total = count_cc([], vcount, clauses, wdir, 7)[3]
    avg = 0
    i = 0

    for f in features:
        fv = [f[0]]
        #print(f)

        if checksat(dimacs_, [fv]):
            # tp = count(dimacs_, [fv])
            tp = count_cc(fv, vcount, clauses, wdir, 7)[3]
            tr = tp/total

            hit = 0
            for s in samples_:
                if str(fv[0]) in s:
                    hit += 1

            sr = hit / len(samples_)

            err = abs(sr-tr)
            i += 1
            avg += err

            #print(err)
    return avg / i


def get_error_smarch(dimacs_, samplefile_):
    _samples = list()
    with open(samplefile_, 'r') as sf:
        for line in sf:
            raw = line.split(',')
            config = raw[:len(raw)-1]
            _samples.append(config)

    return compute_error(dimacs_, _samples)


def get_error_CBDD(dimacs_, samplefile_):
    _samples = list()
    with open(samplefile_, 'r') as sf:
        for line in sf:
            if line.startswith('s:'):
                raw = line.split(':')
                raw = raw[1][:len(raw[1])-2]
                config = raw.split(",")
                _samples.append(config)

    return compute_error(dimacs_, _samples)


def get_error_Unigen2(dimacs_, samplefile_):
    _samples = list()
    with open(samplefile_, 'r') as sf:
        for line in sf:
            raw = line.split()
            if len(raw) != 0:
                raw[0] = raw[0][1:]

                config = raw[:len(raw)-1]
                _samples.append(config)

    return compute_error(dimacs_, _samples)


def get_error_DbS(dimacs_, samplefile_):
    _samples = list()
    init = True
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

                    _samples.append(config)
            else:
                init = False
    return compute_error(dimacs_, _samples)


if __name__ == "__main__":
    sdir = os.path.dirname(os.path.realpath(__file__)) + "/Samples"
    repdir = os.path.dirname(os.path.realpath(__file__)) + "/Replication"
    fmdir = os.path.dirname(os.path.realpath(__file__)) + "/FeatureModel"

    # resfile = os.path.dirname(os.path.realpath(__file__)) + "RQ4_Uniformity.out"
    # rf = open(resfile, 'w')
    # rf.write("target,CBDD,Unigen2,Smarch_basic,Smarch_opt\n")
    # print("target,CBDD,Unigen2,Smarch_basic,Smarch_opt")

    targets = [f.split(".")[0] for f in listdir(fmdir) if isfile(join(fmdir, f))]

    for target in ('ecos-icse11',): #targets:
        # rf.write(target + ",")
        # print(target, end=",", flush=True)
        print(target)
        dimacs = os.path.dirname(os.path.realpath(__file__)) + "/FeatureModel/" + target + ".dimacs"
        ratio = os.path.dirname(os.path.realpath(__file__)) + "/FeatureModel/" + target + ".ratio"
        check_combratio(dimacs, ratio)

        # samplefile = repdir + "/CBDD/" + target + "_97.log"
        # if os.path.exists(samplefile):
        #     error = get_error_CBDD(dimacs, samplefile)
        #     print(error, end=",", flush=True)
        #     rf.write(str(error) + ",")
        # else:
        #     print("N/A", end=",", flush=True)
        #     rf.write("N/A,")
        #
        # samplefile = repdir + "/Unigen2/Samples/" + target + ".txt"
        # if os.path.exists(samplefile):
        #     error = get_error_Unigen2(dimacs, samplefile)
        #     print(error, end=",", flush=True)
        #     rf.write(str(error) + ",")
        # else:
        #     print("N/A", end=",", flush=True)
        #     rf.write("N/A,")
        #
        # samplefile = sdir + "/smarch_basic/" + target + "_97.samples"
        # if os.path.exists(samplefile):
        #     error = get_error_smarch(dimacs, samplefile)
        #     print(error, end=",", flush=True)
        #     rf.write(str(error) + ",")
        # else:
        #     print("N/A", end=",", flush=True)
        #     rf.write("N/A,")
        #
        # samplefile = sdir + "/smarch_mp/" + target + "_97.samples"
        # if os.path.exists(samplefile):
        #     error = get_error_smarch(dimacs, samplefile)
        #     print(error)
        #     rf.write(str(error))
        # else:
        #     print("N/A", flush=True)
        #     rf.write("N/A")

    # rf.close()

