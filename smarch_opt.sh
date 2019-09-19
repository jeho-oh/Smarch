#!bin/bash

# $1: dimacs file
# $2: number of samples

{ python3 ./smarch_opt.py -o ./Samples/smarch_opt -p 7 ./FeatureModel/$1.dimacs $2 ; } 2>&1 | tee ./Samples/smarch_opt/$1_$2.log
