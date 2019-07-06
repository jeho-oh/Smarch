#!bin/bash

# $1: dimacs file
# $2: number of samples

{ time python3 ./smarch_mp.py -o ./Samples/smarch_mp -p 7 ./FeatureModel/$1.dimacs $2 ; } 2>&1 | tee ./Samples/smarch_mp/$1_$2.log
