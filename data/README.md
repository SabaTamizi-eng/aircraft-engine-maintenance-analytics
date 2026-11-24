# Data

Not committed. `python -m pipeline.download_data` puts the raw files in `data/raw/`, and the
other scripts write to `data/processed/` and `data/powerbi/`.

**Source:** NASA Prognostics Center of Excellence, *Turbofan Engine Degradation Simulation
Data Set* (C-MAPSS), from the
[NASA PCoE data set repository](https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/).

**Citation:** A. Saxena, K. Goebel, D. Simon, and N. Eklund, "Damage Propagation Modeling for
Aircraft Engine Run-to-Failure Simulation," in *Proceedings of the 1st International Conference
on Prognostics and Health Management (PHM08)*, Denver, CO, 2008.

| Fleet | Run-to-failure engines | In-service engines | Operating conditions | Fault modes |
|---|---|---|---|---|
| FD001 | 100 | 100 | 1 (sea level) | HPC degradation |
| FD002 | 260 | 259 | 6 | HPC degradation |
| FD003 | 100 | 100 | 1 (sea level) | HPC and fan degradation |
| FD004 | 249 | 248 | 6 | HPC and fan degradation |

Each row is one engine in one cycle: engine number, cycle, 3 operational settings and 21
sensors. Train engines run until they fail; test engines stop earlier and NASA gives their
true RUL in a separate file.

The FD004 counts above are from the files. The readme that comes with the dataset has
them the other way round.
