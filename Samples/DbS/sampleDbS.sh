#!/bin/bash

# $1: target
# $2: samples

createAFiles () {
	file="./$1.a";
          # Write in a-file

	echo "log ./Samples/$1_$2.log" > ${file};
	echo "solver z3" >> ${file};
	echo "vm ./$1.xml" >> ${file} ;
	echo "hybrid distribution-aware distance-metric:manhattan distribution:uniform onlyBinary:true selection:SolverSelection optimization:local number-weight-optimization:1 numConfigs:$2" >> ${file};
	echo "printconfigs ./Samples/$1.csv" >> ${file};
}


# Mono variables
MONO_PATH="/usr/bin/mono"
# SPL Conqueror variables
SPL_CONQUEROR_PATH="/home/jeho-lab/Replication/SPLConqueror/SPLConqueror/CommandLine/bin/Release/CommandLine.exe"

# SPL Conqueror call
createAFiles $1 $2
{ time ${MONO_PATH} ${SPL_CONQUEROR_PATH} ./$1.a ; }  2>> ./Samples/$1_$2.log

if [ $? -ne 0 ]
then 
  echo "An error occurred when performing SPL Conqueror.";
  exit -1; 
fi

