import os
import math


root = os.path.dirname(os.path.abspath(__file__))


def compute_UI(target_, samples_, statfile_):
    _ratiofile = root + "/Ratios/" + target_ + ".ratio"

    trs = list()
    srs = list()
    mes = list()

    eavg = 0
    mecount = 0
    mcount = 0

    _n = len(samples_)

    if _n == 1:
        return "N/A"

    i = 1

    if os.path.exists(_ratiofile):
        with open(_ratiofile, 'r') as _rf:
            for line in _rf:
                tr = float(line)

                hit = 0
                for s in samples_:
                    if (str(i) in s) or (i in s):
                        hit += 1

                sr = hit / len(samples_)

                trs.append(tr)
                srs.append(sr)

                err = abs(sr - tr)
                eavg += err

                se = math.sqrt((tr * (1 - tr)) / _n)
                me = se * 1.96

                mes.append(me)

                if err <= me:
                    mecount += 1

                mcount += 1
                i += 1

        if mcount > 0:
            mecount /= mcount
        else:
            return "ME"

        res = "Pass" if (mecount >= 0.95) else "Fail"

        sf = open(statfile_, "w")
        sf.write("N = " + str(_n) + "\n")
        sf.write("Ratio within margin of error " + str(mecount) + "\n")
        sf.write("Result = " + res + "\n")
        sf.write("\n")

        sf.write("True Ratio,Estimated Ratio\n")
        for i in range(0, len(trs)):
            sf.write(str(trs[i]) + "," + str(srs[i]) + "," + str(mes[i]) + "\n")
        sf.close()

        return mecount


def get_UI_smarch(target_, version_, samplefile_):
    _dimacs = root + "/FeatureModel/" + target + ".dimacs"
    _samples = list()
    with open(samplefile_, 'r') as sf:
        for line in sf:
            raw = line.split(',')
            config = raw[:len(raw)-1]
            _samples.append(config)

    _statfile = root + "/Stats/RQ4/" + target_ + "_" + version_ + "_100" + ".stats"
    return compute_UI(target_, _samples, _statfile)


def get_UI_CBDD(target_, samplefile_):
    _samples = list()
    with open(samplefile_, 'r') as sf:
        for line in sf:
            if line.startswith('s:'):
                raw = line.split(':')
                raw = raw[1][:len(raw[1])-2]
                config = raw.split(",")
                _samples.append(config)

    _statfile = root + "/Stats/RQ4/" + target_ + "_" + "CBDD" + "_100" + ".stats"
    return compute_UI(target_, _samples, _statfile)


def get_error_Unigen2(target_, samplefile_):
    _samples = list()
    with open(samplefile_, 'r') as sf:
        for line in sf:
            raw = line.split()
            if len(raw) != 0:
                raw[0] = raw[0][1:]

                config = raw[:len(raw)-1]
                _samples.append(config)

    _statfile = root + "/Stats/RQ4/" + target_ + "_" + "Unigen2" + "_100" + ".stats"
    return compute_UI(target_, _samples, _statfile)


def get_UI_DDbS(target_, samplefile_):
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

    _statfile = root + "/Stats/RQ4/" + target_ + "_" + "DDbS" + "_100" + ".stats"
    return compute_UI(target_, _samples, _statfile)


def get_UI_QS(target_, samplefile_):
    _samples = list()
    with open(samplefile_, 'r') as sf:
        for line in sf:
            raw = line.split(" ")
            if len(raw) != 0:
                config = raw[:len(raw)-1]
                _samples.append(config)

    _statfile = root + "/Stats/RQ4/" + target_ + "_" + "QS" + "_100" + ".stats"
    return compute_UI(target_, _samples, _statfile)


if __name__ == "__main__":
    sdir = os.path.dirname(os.path.realpath(__file__)) + "/Samples"
    repdir = os.path.dirname(os.path.realpath(__file__)) + "/Replication"
    fmdir = os.path.dirname(os.path.realpath(__file__)) + "/FeatureModel"

    resfile = root + "/Stats/RQ4/summary.out"
    rf = open(resfile, 'w')
    rf.write("target,CBDD,Unigen2,DDbS,QuickSampler,Smarch_basic,Smarch_opt\n")
    print("target,CBDD,Unigen2,DDbS,QuickSampler,Smarch_basic,Smarch_opt")

    # targets = [f.split(".")[0] for f in listdir(fmdir) if isfile(join(fmdir, f))]
    targets = ("lrzip","LLVM","X264","Dune","BerkeleyDBC","HiPAcc","JHipster","Polly","7z","JavaGC","VP9",
               "fiasco_17_10","axtls_2_1_4","fiasco","toybox","axTLS","uClibc-ng_1_0_29","toybox_0_7_5",
               "uClinux","ref4955","adderII","ecos-icse11","m5272c3","pati","olpce2294",
               "integrator_arm9","at91sam7sek","se77x9","phycore229x","busybox-1.18.0","busybox_1_28_0",
               "embtoolkit","freebsd-icse11","uClinux-config","buildroot","freetz","2.6.28.6-icse11",
               "2.6.32-2var","2.6.33.3-2var")

    for target in targets: #("uClinux",):
        rf.write(target + ",")
        print(target, end=",", flush=True)

        samplefile = repdir + "/CBDD/" + target + "_100.log"
        if os.path.exists(samplefile):
            error = get_UI_CBDD(target, samplefile)
            print(error, end=",", flush=True)
            rf.write(str(error) + ",")
        else:
            print("N/A", end=",", flush=True)
            rf.write("N/A,")

        samplefile = repdir + "/Unigen2/Samples/" + target + ".txt"
        if os.path.exists(samplefile):
            error = get_error_Unigen2(target, samplefile)
            print(error, end=",", flush=True)
            rf.write(str(error) + ",")
        else:
            print("N/A", end=",", flush=True)
            rf.write("N/A,")

        samplefile = repdir + "/DbS/Samples/" + target + ".csv"
        if os.path.exists(samplefile):
            error = get_UI_DDbS(target, samplefile)
            print(error, end=",", flush=True)
            rf.write(str(error) + ",")
        else:
            print("N/A", end=",", flush=True)
            rf.write("N/A,")

        samplefile = repdir + "/QuickSampler/Samples/" + target + ".dimacs.samples.valid"
        if os.path.exists(samplefile):
            error = get_UI_QS(target, samplefile)
            print(error, end=",", flush=True)
            rf.write(str(error) + ",")
        else:
            print("N/A", end=",", flush=True)
            rf.write("N/A,")

        samplefile = sdir + "/smarch_base/" + target + "_100.samples"
        if os.path.exists(samplefile):
            error = get_UI_smarch(target, "smarch_base", samplefile)
            print(error, end=",", flush=True)
            rf.write(str(error) + ",")
        else:
            print("N/A", end=",", flush=True)
            rf.write("N/A,")

        samplefile = sdir + "/smarch_opt/" + target + "_100.samples"
        if os.path.exists(samplefile):
            error = get_UI_smarch(target, "smarch_opt", samplefile)
            print(error, end=",", flush=True)
            rf.write(str(error))
        else:
            print("N/A", end=",", flush=True)
            rf.write("N/A,")
        print()
        rf.write("\n")

    rf.close()

