#!bin/bash

# $1: dimacs file
# $2: number of samples

{ time python3 ./smarch_basic.py -o ./Samples/smarch_basic ./FeatureModel/$1.dimacs $2 ; } 2>&1 | tee ./Samples/smarch_basic/$1_$2.log
