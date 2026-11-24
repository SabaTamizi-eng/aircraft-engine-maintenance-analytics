# Data

Data files are not stored in this repository. Run `python -m pipeline.download_data` to
download them into `data/raw/`; the pipeline then writes `data/processed/` and `data/powerbi/`.

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

Each row is one engine in one operating cycle: engine number, cycle, three operational
settings and 21 sensor readings. Run-to-failure ("train") engines run until they fail;
in-service ("test") engines stop before failure, and NASA provides their true remaining
useful life.

**Data quality note:** the dataset readme lists FD004 as 248 run-to-failure and 249
in-service engines, but the files contain 249 and 248. The validation step in
`pipeline/transform.py` caught this, and the pipeline uses the real counts.
