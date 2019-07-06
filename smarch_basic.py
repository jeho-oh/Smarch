"""
Smarch - random sampling of propositional formula solutions
Version - 0.1
"""


import random
from subprocess import getoutput
import pycosat
import os
import sys
import getopt
import time
import shutil


srcdir = os.path.dirname(os.path.abspath(__file__))
SHARPSAT = srcdir + '/sharpSAT/Release/sharpSAT'


def read_dimacs(dimacsfile_):
    """parse variables and clauses from a dimacs file"""

    _features = list()
    _clauses = list()
    _vcount = '-1'  # required for variables without names

    with open(dimacsfile_) as f:
        for line in f:
            # read variables in comments
            if line.startswith("c"):
                line = line[0:len(line) - 1]
                _feature = line.split(" ", 4)
                del _feature[0]
                _feature[0] = int(_feature[0])
                _features.append(tuple(_feature))
            # read dimacs properties
            elif line.startswith("p"):
                info = line.split()
                _vcount = info[2]
            # read clauses
            else:
                info = line.split()
                if len(info) != 0:
                    _clauses.append(list(map(int, info[:len(info)-1])))

    return _features, _clauses, _vcount


def read_constraints(constfile_, features_):
    """read constraint file. - means negation"""
    _const = list()

    if os.path.exists(constfile_):
        names = [i[1] for i in features_]
        with open(constfile_) as file:
            for line in file:
                line = line.rstrip()
                data = line.split()
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
                        print("Added constraint: " + line + " " + str(clause))
                    else:
                        print("Feature not found" + str(clause))
    else:
        print("Constraint file not found")

    return _const


def get_var(flist, features_):
    """convert feature names into variables"""

    _const = list()
    names = [i[1] for i in features_]

    for feature in flist:
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

    f = open(outfile_, 'w')
    f.write('p cnf ' + vars_ + ' ' + str(len(clauses_) + len(constraints_)) + '\n')

    for cl in clauses_:
        f.write(" ".join(str(x) for x in cl) + ' 0 \n')

    for ct in constraints_:
        if isinstance(ct, (list,)):
            line = ""
            for v in ct:
                line = line + str(v) + " "
            f.write(line + '0 \n')
        else:
            f.write(str(ct) + ' 0 \n')

    f.close()


def count(dimacs_, constraints_):
    """count dimacs solutions with given constraints"""

    _tempdimacs = os.path.dirname(dimacs_) + '/count.dimacs'
    _features, _clauses, _vcount = read_dimacs(dimacs_)

    gen_dimacs(_vcount, _clauses, constraints_, _tempdimacs)
    res = int(getoutput(SHARPSAT + ' -q ' + _tempdimacs))

    return res


def checkSAT(dimacs_, constraints_):
    """check satisfiability of given formula with constraints"""
    _features, _clauses, _vcount = read_dimacs(dimacs_)
    cnf = _clauses + constraints_
    s = pycosat.solve(cnf)

    if s == 'UNSAT':
        return False
    else:
        return True


def sample(vcount_, clauses_, n_, wdir_, const_=(), quiet_=False, samplefile_=""):
    """sample configurations"""

    _vars = list()
    for i in range(1, int(vcount_)+1):
        _vars.append(i)

    if not os.path.exists(wdir_):
        os.makedirs(wdir_)

    _samples = list()

    # generate n random numbers for sampling
    def get_random(rcount_, total_):
        def gen_random():
            while True:
                yield random.randrange(1, total_, 1)

        def gen_n_unique(source, n__):
            seen = set()
            seenadd = seen.add
            for i in (i for i in source() if i not in seen and not seenadd(i)):
                yield i
                if len(seen) == n__:
                    break

        return [i for i in gen_n_unique(gen_random, min(rcount_, int(total_ - 1)))]

    # partition space by cubes and count number of solutions for each cube
    def partition(assigned_, number_):
        _cubes = list()
        _selected = list()
        _dimacsfile = wdir_ + '/dimacs.smarch'
        _cubefile = wdir_ + '/cubes.smarch'

        res = 0

        # get variable to partition
        _pv = _varspace.pop()
        _cubes.append([_pv])
        _cubes.append([-1 * _pv])

        # execute sharpSAT to count solutions
        for _cube in _cubes:
            gen_dimacs(vcount_, clauses_, assigned_ + _cube, _dimacsfile)

            if checkSAT(_dimacsfile, []):
                res = int(getoutput(SHARPSAT + ' -q ' + _dimacsfile))
            else:
                res = 0

            if number_ <= res:
                _selected = _cube.copy()
                break
            else:
                number_ = number_ - res

        _allfree = False
        if res == (2 ** len(_varspace)):
            _allfree = True

        return _selected, number_, _allfree

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

    clauses_ = clauses_ + const_

    if not quiet_:
        print("Counting - ", end='')

    gen_dimacs(vcount_, clauses_, [], wdir_ + '/dimacs.smarch')
    total = int(getoutput(SHARPSAT + ' -q ' + wdir_ + '/dimacs.smarch'))

    if not quiet_:
        print("Total configurations: " + str(total), flush=True)

    # generate random numbers
    rands = get_random(n_, total)

    if samplefile_ != "":
        f = open(samplefile_, "w")
    else:
        f = ""

    # sample for each random number
    i = 1
    for r in rands:
        if not quiet_:
            print("Sampling " + str(i) + " with " + str(r) + " - ", end='', flush=True)
        sample_time = time.time()

        # initialize variables
        number = r
        _varspace = _vars.copy()
        assigned = list()

        # recurse
        while not len(_varspace) == 0:
            cube, number, allfree = partition(assigned, number)

            # select cube to recurse
            assigned = assigned + cube

            if allfree:
                assigned = assigned + set_freevar(_varspace, int(number))
                break

            if len(cube) == 0:
                print("ERROR: cube not selected")
                exit()

        # verify if sample is valid and assign dead variables using pycosat
        assigned = list(map(int, assigned))
        aclause = [assigned[i:i+1] for i in range(0, len(assigned))]
        cnf = clauses_ + aclause
        s = pycosat.solve(cnf)

        if s == 'UNSAT':
            print("ERROR: Sample Invalid")
            exit(1)
        else:
            if samplefile_ == "":
                _samples.append(set(s))
            else:
                for v in s:
                    f.write(str(v))
                    f.write(",")
                f.write("\n")

        if not quiet_:
            print("sampling time: " + str(time.time() - sample_time), flush=True)

        i += 1

    shutil.rmtree(wdir_)

    if samplefile_ != "":
        f.close()

    return _samples


if __name__ == "__main__":
    # # test script
    # n = 97
    # target = "axtls_2_1_4"
    #
    # dimacs = srcdir + "/FeatureModel/" + target + ".dimacs"
    # constfile = ""
    # wdir = os.path.dirname(dimacs) + "/smarch"
    #
    # features, clauses, vcount = read_dimacs(dimacs)
    # const = read_constraints(constfile, features)
    #
    # start_time = time.time()
    # samples = sample(vcount, clauses, n, wdir, const, False)
    # print("--- total time: %s seconds ---" % (time.time() - start_time))

    # run script
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

    # get parameters from console
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hc:o:q", ['help', "cfile=", "odir=", 'quiet'])
    except getopt.GetoptError:
        print('smarch.py -c <constfile> -o <outputdir>  -q | <dimacsfile> <samplecount>')
        sys.exit(2)

    if len(args) < 2:
        print('smarch.py -c <constfile> -o <outputdir>  -q | <dimacsfile> <samplecount>')
        sys.exit(2)

    dimacs = args[0]
    base = os.path.basename(dimacs)
    target = os.path.splitext(base)[0]
    n = int(args[1])

    print('Input file: ', dimacs)
    print('Number of samples: ', n)

    wdir = os.path.dirname(dimacs) + "/smarch"
    constfile = ''
    samplefile = ""
    quiet = False
    out = False

    #  process parameters
    for opt, arg in opts:
        if opt == '-h':
            print('smarch.py -c <constfile> -o <outputdir> -q | <dimacsfile> <samplecount>')
            sys.exit()
        elif opt in ("-c", "--cfile"):
            constfile = arg
            print("Consraint file: " + constfile)
        elif opt in ("-o", "--odir"):
            odir = arg
            wdir = odir + "/smarch"
            samplefile = odir + "/" + target + "_" + str(n) + ".samples"
            out = True
            print("Output directory: " + wdir)
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
    samples = sample(vcount, clauses, n, wdir, const, quiet, samplefile)
    if not quiet:
        print("--- total time: %s seconds ---" % (time.time() - start_time))
