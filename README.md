# SpynWave
A python package for propagating spin wave spectroscopy measurements.

## Installation
### Prerequisites
To install the software you need a Python installation, newer than version 3.8.
If there is no Python installed, Miniconda or Anaconda (https://www.anaconda.com/products/distribution) are highly recommended.

Depending on how you install the package, you might also need an installation of Git (https://git-scm.com/).
Alternatively, you can manually copy the files.

Finally, the software also needs a running VISA library (such as NI-VISA, but for most lab-PCs, the VISA library by National Instruments is already installed.)

### Installation and update using git
To install the package directly using git (which is the easiest way, if Git is installed), simply run:
```commandline
pip install -U git+https://gitlab.tue.nl/fna/spynwave.git
```

### Installation from a local copy
If you made a local copy (either manually or by cloning the repository using git) you can install the package by opening a command prompt in the copied folder (the directory containing the file `pyproject.toml`).
In this folder, run:
```commandline
pip install -e .
```
Here the `-e` (which is optional) makes the package editable, allowing you to make modifications to the package without having to reinstall it.

### Initialization
To increase the ease of use, run the following command
```commandline
python -m spynwave --init
```
This will create a desktop shortcut to the software and copy the configuration and calibration files to an easily accessible place (a "spynwave" folder in the user home directory.)

Note that running this initialization will overwrite the files that are currently in the "spynwave" folder in the user home directory (if there are any).
This means that any configuration or calibration that is stored in that folder is possibly erased.

### Configuring the measurement setup
When the software is executed, it will load configuration from a file called "config.yaml" in the "spynwave" folder in the user home directory (e.g. C:/users/PhysFna2/spynwave).
This yaml file contains a lot of configuration regarding the setup.
The most important attribute is the general - magnet property, which controls whatever setup the software runs on and should be adjusted accordingly.
This property can be set to one of the following three options: "in-plane magnet", "out-of-plane magnet", "cryo magnet".

This file also contains the addresses of the instruments (e.g. under in-plane magnet: power-supply: address, or source-meter: address) and for some instruments (e.g. the Keithley 2400 source-meter) also some communication setting.
You can have a look at these setting (and modify them as needed) when there are communication issues (or if you changed addresses).

### Note for using the in-plane magnet
When you want to use the in-plane magnet, you additionally need drivers to control the LabJack (U12) that is used to select the polarity of the magnet.
These drivers can be found on the [website of LabJack](https://labjack.com/pages/support?doc=/software-driver/installer-downloads/u12-software-installer-u12/), or in the requirements folder of this repository.

## Usage
If the initialization has been run, you can start the software by double-clicking the shortcut on the desktop.

Alternatively, you can run the software from a command window by running:
```commandline
python -m spynwave
```

To view all the possible options that this command takes, use:
```commandline
python -m spynwave -h
```

### Filenames
The filename can be filled automatically with parameter (input) values by referencing the name of the input parameter (i.e. the label associated with the input parameter).
For example, to put the CW frequency (for a field sweep) in the filename, you can use a filename `PSWS_{Magnetic field}mT`.
This uses the standard python string formatting techniques (e.g. to have a constant number of digits with no decimals, you can use `{Magnetic field:03.0f}`).
Presently that list contains:
`Advanced RF settings`, `Apply DC excitation`, `Averaging type`, `CW Frequency`,
`Current sweep rate`, `DC current`, `DC current compliance`, `DC voltage`, `DC voltage compliance`,
`Field sweep rate`, `Filename base`, `Folder`, `Frequency step size`, `Magnetic field`,
`Measurement ports`, `Number of averages (VNA)`, `Perform with mirrored field`, `RF bandwidth`,
`RF output power`, `Saturate field before measurement`, `Saturation `, `Saturation field`,
`Source-meter regulate`, `Start current`, `Start field`, `Start frequency`, `Start voltage`,
`Stop current`, `Stop field`, `Stop frequency`, `Stop voltage`, `Time sweep duration`,
`Type of measurement`, `Voltage sweep rate`.
I assume that the most names speak for themselves; the sweep-values contain terms as `start`, `Stop`, `step size`, `sweep rate`.
Static values (if others are sweeping) are `CW Frequency`, `DC current`, `DC voltage`, and `Magnetic field`.

### Calibrating the magnet
When a new calibration for a magnet is required, this can be done using the packed calibration software.
To run this software, open a command window and run:
```commandline
python -m spynwave -M
```

A window will open that allows you to calibrate the magnet.
After the calibration is finished, the file should be placed in the "spynwave" folder in the user home directory (e.g. C:/users/PhysFna2/spynwave) and the filename should match the filename for the calibration that is mentioned in the config.yaml file for the specific setup.
