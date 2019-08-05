# Pyrocko

### _A seismology toolkit for Python_
[![Anaconda-Server Badge](https://anaconda.org/pyrocko/pyrocko/badges/installer/conda.svg)](https://conda.anaconda.org/pyrocko) [![PyPI](https://img.shields.io/pypi/v/pyrocko.svg)](https://pypi.python.org/pypi/pyrocko/)


## Announcement: Pyrocko is leaving GitHub

*Potsdam, 2019-08-05*

Since last week, [GitHub is restricting access to their services based on
user nationality and residence](https://help.github.com/en/articles/github-and-trade-controls>) ([see
also](https://techcrunch.com/2019/07/29/github-ban-sanctioned-countries)).
Such restrictions are incompatible with scientific standards in
international research communities like seismology.

The Pyrocko software package is used by researchers worldwide, in
at least 44 countries. As researchers, we are obligated to retain open
access to all. To achieve this, we are now migrating our code repositories
away from GitHub to a new safe home. The new home of the Pyrocko repository
is at [git.pyrocko.org](https://git.pyrocko.org/pyrocko/), open now.

To ensure a smooth
transition, we will keep a read-only version of the Pyrocko code repository
at GitHub until 2019-10-01, when it will be deleted.

To update the upstream url of a cloned Pyrocko repository, run

```
git remote set-url origin https://git.pyrocko.org/pyrocko/pyrocko.git
```

in the cloned directory.

To obtain a fresh clone, run

```
git clone https://git.pyrocko.org/pyrocko/pyrocko.git pyrocko
```

Thanks to the worldwide seismology community for all the support and help.

Best regards

*The Pyrocko Developers*


## Installation

Full installation instructions are available at 
https://pyrocko.org/docs/current/install/.

### Installation from source

```
git clone https://git.pyrocko.org/pyrocko/pyrocko
cd pyrocko
sudo python setup.py install_prerequisites
sudo python setup.py install
```

### Anaconda / MacOSX

```
conda install -c pyrocko pyrocko
```
Anaconda2/3 Packages are available for Linux and OSX

### Python PIP

```
sudo pip install pyrocko
```

or from source

```
git clone https://git.pyrocko.org/pyrocko/pyrocko
cd pyrocko
sudo pip install -r requirements.txt
sudo pip install .
```


## Documentation

Documentation and usage examples are available online at https://pyrocko.org/docs/current

## Community Support

Community support at [https://hive.pyrocko.org](https://hive.pyrocko.org/signup_user_complete/?id=9edryhxeptdbmxrecbwy3zg49y).

## Citation
The recommended citation for Pyrocko is: (You can find the BibTeX snippet in the
[`CITATION` file](CITATION.bib)):

> Heimann, Sebastian; Kriegerowski, Marius; Isken, Marius; Cesca, Simone; Daout, Simon; Grigoli, Francesco; Juretzek, Carina; Megies, Tobias; Nooshiri, Nima; Steinberg, Andreas; Sudhaus, Henriette; Vasyura-Bathke, Hannes; Willey, Timothy; Dahm, Torsten (2017): Pyrocko - An open-source seismology toolbox and library. V. 0.3. GFZ Data Services. https://doi.org/10.5880/GFZ.2.1.2017.001

[![DOI](https://img.shields.io/badge/DOI-10.5880%2FGFZ.2.1.2017.001-blue.svg)](https://doi.org/10.5880/GFZ.2.1.2017.001)

## License 
GNU General Public License, Version 3, 29 June 2007

Copyright © 2017 Helmholtz Centre Potsdam GFZ German Research Centre for Geosciences, Potsdam, Germany

Pyrocko is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
Pyrocko is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with this program. If not, see <http://www.gnu.org/licenses/>.

## Contact
* Sebastian Heimann; 
  sebastian.heimann@gfz-potsdam.de

* Marius Isken; 
  marius.isken@gfz-potsdam.de

* Marius Kriegerowski; 
  marius.kriegerowski@gfz-potsdam.de

```
Helmholtz Centre Potsdam German Research Centre for Geoscienes GFZ
Section 2.1: Physics of Earthquakes and Volcanoes
Helmholtzstraße 6/7
14467 Potsdam, Germany
```
