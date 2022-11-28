# SpynWave
A python package for propagating spin wave spectroscopy measurements.

## Installation
### Prerequisites
To install the software you need a Python installation, newer than version 3.8.
If there is no Python installed, Miniconda or Anaconda (https://www.anaconda.com/products/distribution) are highly recommended.

Depending on how you install the package, you might also need an installation of Git (https://git-scm.com/).
Alternatively, you can manually copy the files.

Finally, the software also needs a running VISA library (such as NI-VISA, but for most lab-PCs, the VISA library by National Instruments is already installed.)

### Installation using git
To install the package directly using git (which is the easiest way, if Git is installed), simply run:
```commandline
pip install git+https://gitlab.tue.nl/fna/psws-python-measurement-suite.git
```

### Installation from a local copy
If you made a local copy (either manually or by cloning the repository using git) you can install the package by opening a command prompt in the copied folder (the directory containing the file `pyproject.toml`).
In this folder, run:
```commandline
pip install -e .
```
Here the `-e` (which is optional) makes the package editable, allowing you to make modifications to the package without having to reinstall it.

### Note for using the in-plane magnet
When you want to use the in-plane magnet, you additionally need drivers to control the LabJack (U12) that is used to select the polarity of the magnet.
These drivers can be found on the [website of LabJack](https://labjack.com/pages/support?doc=/software-driver/installer-downloads/u12-software-installer-u12/), or in the requirements folder of this repository.

## Usage

### Performing a magnet calibration.

