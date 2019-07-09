"""
Smarch - random sampling of propositional formula solutions
Version - 0.1
"""


import random
from subprocess import getoutput
import pycosat
import os
import shutil
import time
import sys
import getopt
import math

import multiprocessing


srcdir = os.path.dirname(os.path.abspath(__file__))
SHARPSAT = srcdir + '/sharpSAT/Release/sharpSAT'
MARCH = srcdir + '/CnC/march_cu/march_cu'

DEBUG = False


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


def read_constraints(constfile_, features_):
    """read constraint file. - means negation"""

    _const = list()

    if os.path.exists(constfile_):
        names = [i[1] for i in features_]
        with open(constfile_) as file:
            for _line in file:
                _line = _line.rstrip()
                data = _line.split()
                if len(data) != 0:
                    clause = list()

                    error = False
                    for name in data:
                        prefix = 1
                        if name.startswith('-'):
                            name = name[1:len(name)]
                            prefix = -1

                        if name in names:
                            i = names.index(name)
                            clause.append(features_[i][0] * prefix)
                        else:
                            error = True
                            clause.append(name)

                    if not error:
                        _const.append(clause)
                        print("Added constraint: " + _line + " " + str(clause))
                    else:
                        print("Feature not found" + str(clause))
    else:
        print("Constraint file not found")

    return _const


def get_var(flist_, features_):
    """convert feature names into variables"""

    _const = list()
    names = [i[1] for i in features_]

    for feature in flist_:
        prefix = 1
        if feature.startswith('-'):
            feature = feature[1:len(feature)]
            prefix = -1

        # filter features that does not exist
        if feature in names:
            i = names.index(feature)
            _const.append(prefix * features_[i][0])

    return _const


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

            if DEBUG:
                print(str(pid) + ":" + str(cres))

            _sol.append(cres)

        q_.put([cubes_, _sol])

        shutil.rmtree(wdir_ + '/' + str(pid))

    # create dimacs file regarding constraints
    gen_dimacs(vcount_, clauses_, assigned_, _dimacsfile)

    # execute march to get cubes
    res = getoutput(MARCH + ' ' + _dimacsfile + ' -d 5 -#')
    _out = res.split("\n")

    # # print march result (debugging purpose)
    if DEBUG:
        print(_out)

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

                if DEBUG:
                    print(res)

                _total += res
                _counts.append(res)

    return _freevar, _counts, _cubes, _total, _allfree


def master(vcount_, clauses_, n_, wdir_, const_=(), threads_=1, quiet_=False):
    """generate random numbers and manage sampling processes"""

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

    clauses_ = clauses_ + const_

    if not quiet_:
        print("Counting - ", end='', flush=True)

    count_time = time.time()
    ccres = count_cc([], vcount_, clauses_, wdir_, threads_)

    if not quiet_:
        print("Total configurations: " + str(ccres[3]))
        print("Counting time: " + str(time.time() - count_time))

    # prevent oversampling
    if ccres[3] < n_:
        n_ = ccres[3]

    # generate random numbers
    rands = get_random(n_, ccres[3])
    rands.sort()

    # partition random numbers for each thread
    chunk = math.ceil(n_ / threads_)
    pnum = math.ceil(n_/chunk)

    rlist = list()
    for i in range(0, pnum):
        rlist.append(rands[i*chunk: (i+1)*chunk])

    # run sampling processes
    _samples = list()
    with multiprocessing.Manager() as manager:
        q = manager.Queue()
        plist = list()

        # create processes
        for i in range(0, len(rlist)):
            plist.append(
                multiprocessing.Process(target=sample,
                                        args=(q, vcount_, clauses_, rlist[i], wdir_, ccres, quiet_)))

        # start processes
        for p in plist:
            p.start()

        # wait until processes are finished
        for p in plist:
            p.join()

        # gather samples
        while not q.empty():
            _samples.append(q.get())
            # sset = q.get()
            # for s in sset:
            #     samples.append(s)

    return _samples


def sample(q, vcount_, clauses_, rands_, wdir_, ccres_, quiet_=False):
    """sample configurations"""
    # create folder for file IO of this process
    pid = os.getpid()
    _wdir = wdir_ + "/" + str(pid)
    if not os.path.exists(_wdir):
        os.makedirs(_wdir)

    cache_b = dict()
    cache_c = dict()

    # select a cube based on given random number
    def select_cube(counts_, cubes_, number_):
        _terminate = False
        _index = -1
        _i = 0

        for c in counts_:
            if number_ <= c:
                _index = _i
                if c == 1:
                    _terminate = True
                break
            else:
                number_ -= c
            _i += 1

        return cubes_[_index], number_, _terminate

    # assign free variables without recursion
    def set_freevar(fv_, number_):
        _vars = list()

        for _v in fv_:
            if number_ % 2 == 1:
                _vars.append(_v)
            else:
                _vars.append('-'+_v)
            number_ //= 2

        return _vars

    # partition space by cubes and count number of solutions for each cube
    def traverse(assigned_, r_):
        _cubes = list()
        _freevar = list()
        _selected = list()
        _terminate = False
        _dimacsfile = _wdir + '/dimacs.smarch'
        _cubefile = _wdir + '/cubes.smarch'
        cube_time = 0
        _allfree = False

        # get list of cubes
        if tuple(assigned_) in cache_b:
            _cubes = cache_b[tuple(assigned_)][0]
            _freevar = cache_b[tuple(assigned_)][1]
            _allfree = cache_b[tuple(assigned_)][2]
        else:
            # create dimacs file regarding constraints
            gen_dimacs(vcount_, clauses_, assigned_, _dimacsfile)

            # execute march to get cubes
            cube_time = time.time()
            res = getoutput(MARCH + ' ' + _dimacsfile + ' -d 2 -#')
            _out = res.split("\n")
            cube_time = time.time() - cube_time

            for _line in _out:
                if _line.startswith("c free"):
                    _freevar = _line.split(": ")[1].split()
                elif _line.startswith('c all'):
                    _allfree = True
                elif _line.startswith('a'):
                    _cube = list(_line.split())
                    _cube = _cube[1:len(_cube) - 1]
                    _cubes.append(_cube)

            # print march result (debugging purpose)
            if DEBUG:
                print(_out)
                print(_freevar)

            # double check all variables are free
            if _allfree:
                total = int((getoutput(SHARPSAT + ' -q ' + _dimacsfile)))
                if total != 2 ** (len(_freevar)):
                    _freevar.clear()
                    _allfree = False

        # select a cube with counting
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
            # print cubes (debugging purpose)
            if DEBUG:
                print(_cubes)
                print("r:" + str(r_))

            # execute sharpSAT to count solutions and select partition
            _count = 0

            for i in range(0, len(_cubes)):
                # reuse count if cached
                if tuple(assigned_ + _cubes[i]) in cache_c:
                    _count = cache_c[tuple(assigned_ + _cubes[i])]
                else:
                    # count size of partition
                    count_time = time.time()
                    gen_dimacs(vcount_, clauses_, assigned_ + _cubes[i], _dimacsfile)

                    _count = int(getoutput(SHARPSAT + ' -q ' + _dimacsfile))

                    # print count (debugging purpose)
                    if DEBUG:
                        print(str(i) + ":" + str(_count))

                    # cache count data if sharpSAT runtime exceeds 0.02 seconds
                    if time.time() - count_time > 0.05:
                        cache_c[tuple(assigned_ + _cubes[i])] = _count

                # get selected cube
                if r_ <= _count:
                    _selected = _cubes[i].copy()
                    break
                else:
                    if i == (len(_cubes) - 2):
                        _selected = _cubes[i+1].copy()
                        r_ = r_ - _count
                        break
                    else:
                        r_ = r_ - _count

            # 1 solution left: sampling done
            if _count == 1:
                _terminate = True

            # cache cube data if sharpSAT runtime exceeds 0.02 seconds
            if cube_time > 0.05:
                cache_b[tuple(assigned_)] = (_cubes, _freevar, _allfree)

        return _selected, r_, _freevar, _allfree, _terminate

    # sample for each random number
    i = 1
    _sample = list()

    for r in rands_:

        sample_time = time.time()

        # initialize variables
        number = r
        assigned = list()

        if ccres_[4]:  # all variables free, sampling done
            assigned = assigned + set_freevar(ccres_[0], int(number))
            terminate = True
        else:  # select cube to recurse
            cube, number, terminate = select_cube(ccres_[1], ccres_[2], number)
            assigned = assigned + cube

            if len(cube) == 0:
                print("ERROR: cube not selected", flush=True)
                exit()

        # recurse
        while not terminate:
            cube, number, freevar, terminate, allfree = traverse(assigned, number)

            if terminate:
                assigned = assigned + cube
            elif allfree:  # all variables free, sampling done
                assigned = assigned + set_freevar(freevar, int(number))
                terminate = True
            else:  # select cube to recurse
                assigned = assigned + cube

                if len(cube) == 0:
                    print("ERROR: cube not selected: " + str(len(freevar)), flush=True)
                    exit()

        # verify if sample is valid and assign dead variables using pycosat
        assigned = list(map(int, assigned))
        aclause = [assigned[i:i+1] for i in range(0, len(assigned))]
        cnf = clauses_ + aclause
        _sol = pycosat.solve(cnf)

        if _sol == 'UNSAT':
            print("ERROR: Sample Invalid", flush=True)
            exit(1)
        else:
            # _sample.append(s)
            q.put(_sol)

        if not quiet_:
            print(str(pid) + ": Sampled " + str(i) + " with " + str(r) + " - ", end='')
            print("sampling time: " + str(time.time() - sample_time), flush=True)
        i += 1

    # q.put(_sample)
    shutil.rmtree(_wdir)

    return


if __name__ == "__main__":
    # test = True
    # if test:
    #     # test script
    #     n = 192
    #     target = "Apache"
    #
    #     dimacs = srcdir + "/FeatureModel/" + target + ".dimacs"
    #     constfile = os.path.dirname(dimacs) + "/constraints.txt"
    #     wdir = os.path.dirname(dimacs) + "/smarch"
    #
    #     features, clauses, vcount = read_dimacs(dimacs)
    #     const = read_constraints(constfile, features)
    #
    #     start_time = time.time()
    #     samples = master(vcount, clauses, n, wdir, const, 1, False)
    #     print("--- total time: %s seconds ---" % (time.time() - start_time))
    #
    #     sys.exit(0)

    # run script
    # get external location for sharpSAT and march if needed
    if os.path.exists(srcdir + "/links.txt"):
        with open(srcdir + "/links.txt") as f:
            for line in f:
                link = list(line.split('='))
                if len(link) != 0 and link[0][0] != '#':
                    if link[0] == "SHARPSAT":
                        SHARPSAT = link[1]
                    elif link[0] == "MARCH":
                        MARCH = link[1]

    # check sharpSAT and march_cu existence
    if not os.path.exists(SHARPSAT):
        print("ERROR: sharpSAT not found")

    if not os.path.exists(MARCH):
        print("ERROR: March solver not found")

    # get parameters from console
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hc:o:p:q", ['help', "cfile=", "odir=", "threads=", 'quiet'])
    except getopt.GetoptError:
        print('smarch.py -c <constfile> -o <outputdir> -p <threads> -q | <dimacsfile> <samplecount>')
        sys.exit(2)

    if len(args) < 2:
        print('smarch.py -c <constfile> -o <outputdir> -p <threads> -q | <dimacsfile> <samplecount>')
        sys.exit(2)

    dimacs = args[0]
    n = int(args[1])

    print('Input file: ', dimacs)
    print('Number of samples: ', n)

    wdir = os.path.dirname(dimacs) + "/smarch"
    constfile = ''
    quiet = False
    out = False
    threads = 1

    #  process parameters
    for opt, arg in opts:
        if opt == '-h':
            print('smarch.py -c <constfile> -o <outputdir> -p <threads> -q | <dimacsfile> <samplecount>')
            sys.exit()
        elif opt in ("-c", "--cfile"):
            constfile = arg
            print("Consraint file: " + constfile)
        elif opt in ("-o", "--odir"):
            wdir = arg
            out = True
            if not os.path.exists(wdir):
                os.makedirs(wdir)
            print("Output directory: " + wdir)
        elif opt in ("-p", "--threads"):
            threads = int(arg)
        elif opt in ("-q", "--quiet"):
            quiet = True
        else:
            print("Invalid option: " + opt)

    # create working directory for smarch and CnC
    # create folder for file IO of this process
    if not os.path.exists(wdir):
        os.makedirs(wdir)

    # process dimacs file
    features, clauses, vcount = read_dimacs(dimacs)
    const = list()
    if constfile != '':
        read_constraints(constfile, features)

    # sample configurations
    start_time = time.time()
    samples = master(vcount, clauses, n, wdir, const, threads, quiet)
    if not quiet:
        print("--- total time: %s seconds ---" % (time.time() - start_time))

    # output samples to a file
    base = os.path.basename(dimacs)
    target = os.path.splitext(base)[0]
    samplefile = wdir + "/" + target + "_" + str(n) + ".samples"

    if out:
        of = open(wdir + "/" + target + "_" + str(n) + ".samples", 'w')
        for s in samples:
            for v in s:
                of.write(str(v))
                of.write(",")
            of.write("\n")
        of.close()

        print('Output samples created on: ', samplefile)
