# SciLab

SciLab is a Python-based application for controlling laboratory equipment, specifically lasers and a spectrometer, to perform automated measurements. It provides a graphical user interface for managing experiment plans, viewing live data, and analyzing results.

## Features

*   **Automated Measurements**: Define and execute measurement plans using different lasers.
*   **Live Spectrum View**: View the spectrometer readings in real-time.
*   **Data Analysis**: Analyze the captured data, including polynomial fitting.
*   **Automatic Port Detection**: Automatically detects and connects to OBIS and CUBE lasers, even if their serial ports change.
*   **GUI-based Port Management**: Easily view, edit, and rescan for laser serial ports directly from the user interface.
*   **Configurable**: Measurement parameters and hardware settings can be configured via a `SciLab.yaml` file.
*   **Command-Line Interface**: A CLI is available for running measurements and analysis without the GUI.

## Screenshots

### Run Plan View
The Run Plan view is where you can configure and start your measurement runs. You can enable/disable specific lasers and manage serial port connections.
<img src="assets/Run_view.png" alt="Run Plan" width="900">

### Live View
The Live View provides a real-time plot of the spectrometer readings.
<img src="assets/Live_view.png" alt="Live View" width="900">

### Analysis View
The Analysis view is used to load and analyze completed measurement runs.
<img src="assets/Analysis_view.png" alt="Analysis" width="900">

## Usage

To run the application, execute the `main` function in `ui/app.py`:

```bash
python -m ui.app
```

Alternatively, you can use the command-line interface:

```bash
python -m cli.spectro --help
```

## Configuration

The application can be configured using a `SciLab.yaml` file in the root directory. If this file is not present, a default configuration will be used.

The configuration file allows you to set:
*   Serial port settings for the lasers and other devices.
*   Laser-specific parameters (e.g., power levels, channels).
*   Measurement parameters (e.g., integration time, number of samples).
*   Output directory for saving data.
