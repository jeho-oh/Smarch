from smarch_opt import master, read_dimacs, read_constraints
import os
import time
import sys
import getopt
import shutil

srcdir = os.path.dirname(os.path.abspath(__file__))
SHARPSAT = srcdir + '/sharpSAT/Release/sharpSAT'
MARCH = srcdir + '/CnC/march_cu/march_cu'

def is_int(s):
    try:
        int(s)
        return True
    except ValueError:
        return False

def gen_configs(features_, samples_, cdir_):
    # remove existing contents on the folder
    for f in os.listdir(cdir_):
        file_path = os.path.join(cdir_, f)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(e)

    # generate .config files from samples
    i = 0
    for s in samples_:
        config = ""
        for sel in s:
            feature = features_[abs(sel) - 1]

            if sel > 0:
                if feature[2] == 'nonbool':
                    config = config + feature[1] + "=" + feature[3] + "\n"
                else:
                    config = config + feature[1] + "=y\n"

            elif sel < 0:
                if feature[2] == 'nonbool':
                    if is_int(feature[3]):
                        config = config + feature[1] + "=0\n"
                    else:
                        config = config + feature[1] + "=\"\"\n"
                else:
                    config = config + "# " + feature[1] + " is not set\n"

        with open(cdir_ + "/" + str(i) + ".config", 'w') as outfile:
            outfile.write(config)
            outfile.close()

        i += 1

    #print("Configs generated")


if __name__ == "__main__":
    
    
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
        opts, args = getopt.getopt(sys.argv[1:], "hc:o:p:q", ['help', "cfile=", "threads=", 'quiet'])
    except getopt.GetoptError:
        print('kconfigGen.py -c <constfile> -p <threads> -q | <dimacsfile> <samplecount>, <outdir>')
        sys.exit(2)

    if len(args) < 3:
        print('kconfigGen.py -c <constfile> -p <threads> -q | <dimacsfile> <samplecount> <outdir>')
        sys.exit(2)

    dimacs = args[0]
    n = int(args[1])

    out = True
    odir = args[2]

    if not os.path.exists(odir):
        os.makedirs(odir)

    print('Input file: ', dimacs)
    print('Number of samples: ', n)
    print("Output folder: ", odir)

    wdir = os.path.dirname(odir) + "/smarch"
    constfile = ''
    quiet = False
    out = False
    threads = 1

    #  process parameters
    for opt, arg in opts:
        if opt == '-h':
            print('kconfigGen.py -c <constfile> -p <threads> -q | <dimacsfile> <samplecount>')
            sys.exit()
        elif opt in ("-c", "--cfile"):
            constfile = arg
            print("Consraint file: " + constfile)
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
        const = read_constraints(constfile, features)

    # sample configurations
    start_time = time.time()
    samples = master(vcount, clauses, n, wdir, const, threads, quiet)
    if not quiet:
        print("--- total time: %s seconds ---" % (time.time() - start_time))

    # output samples to a file
    gen_configs(features, samples, odir)
    print('Output samples created on: ', odir)
