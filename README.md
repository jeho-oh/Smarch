# Smarch
Smarch is a tool to uniform sample solutions of a propositional formula, primarily developed for uniform sampling Software Product Line configurations.

Smarch maintains a one-to-one correspondence between integers and configurations, converting uniformly sampled integers into uniformly sampled configurations. As Smarch only creates configurations that are used as samples, it has better scalability than other uniform sampling algorithms. Smarch can be optimized with respect to variable selection, parallelism, and caching to reduce its sampling time.

For more descirption on how it works, please refer to: https://apps.cs.utexas.edu/apps/tech-reports/192690

## Prerequisites
Smarch relies on following tools:
* sharpSAT (https://github.com/marcthurley/sharpSAT): A exact model counting tool. To build, run make inside Release folder.
* march_cu (https://github.com/marijnheule/CnC): Solver based on cube-and-conquer algorithm. To build, run make inside folder.

Repository of both tools are included here as submodules.  
Note that, the tools have slighlty modified output with the original version, but their functionality is the same.

Smarch python script uses following additional package: pycosat

## How to run
```python
python3 smarch_opt.py -c <constfile> -o <outputdir> -p <processes> -q | <dimacsfile> <samplecount>
```
* dimacsfile: Location of the dimacs file.
* samplecount: Number of samples to create.
* constfile: Location of the constraint file. (default: none)
* outputdir: Directory to create the output files. (default: (dimacs location)/smarch) 
* processes: Number of processes to sample in parallel
* -q: Quiet mode

## Output
On the specified outputdir, .samples file lists the samples.
Each line represents a sample, which is a list of variables.
Positive value means true is assigned, negative value means false is assigned.
