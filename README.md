[![CI](https://github.com/pyccino/StaMPS/actions/workflows/ci.yml/badge.svg?branch=windows-port/main)](https://github.com/pyccino/StaMPS/actions/workflows/ci.yml)

# StaMPS - Stanford Method for Persistent Scatterers

## Description
**StaMPS** is a software package that allows to extract ground displacements from time series of synthetic aperture radar (SAR) acquisitions. The package incorporates persistent scatterer and small baseline methods plus an option to combine both approaches. It is compatible with the **TRAIN** software and therefore allows to incorporate various tropospheric correction methods in the processing workflow.

## Installation
See the **StaMPS** manual for installation details and dependencies.

On Windows, follow the native install flow documented in
[`INSTALL.md`](./INSTALL.md) (SNAP preprocessor path). The upcoming
`v1.0.0` tag on the [pyccino/StaMPS](https://github.com/pyccino/StaMPS)
fork marks the first release of the Windows port.

## Required OS
- Linux (any modern distribution) — full support for all preprocessor paths.
- macOS — supported for ISCE/SNAP/DORIS+ROI_PAC paths.
- Windows 10 21H2+ / Windows 11 (x64) — supported end-to-end for the
  **SNAP** preprocessor path only. See [`INSTALL.md`](./INSTALL.md) for
  the native Windows install flow. WSL users should follow the Linux
  install flow inside the WSL distribution.

## Supported InSAR pre-processors:
- ISCE
- GAMMA
- SNAP
- DORIS + ROI_PAC

## Development
The original version was developed at Stanford University but subsequent development has taken place mainly at the University of Iceland, Delft University of Technology and the University of Leeds. In addition, there have been community contributions.

## Contributors
- Andy Hooper (Lead)
- David Bekaert
- Karsten Spaans
- Ekbal Hussain
- Mahmut Arikan
- Anneleen Oyen
- Miguel Caro Cuenca
- Jose Manuel Delgado Blasco
- *other commmunity members*

https://github.com/dbekaert/stamps/graphs/contributors

**Community contributions are welcomed.**

## Contact details
*Andy Hooper\
COMET\
School of Earth and Environment\
University of Leeds\
Leeds, LS2 9JT*
