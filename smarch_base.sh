#!bin/bash

# $1: dimacs file
# $2: number of samples

{ python3 ./smarch_base.py -o ./Samples/smarch_base ./FeatureModel/$1.dimacs $2 ; } 2>&1 | tee ./Samples/smarch_base/$1_$2.log
