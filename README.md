# Bird 5019 RS-232 Reader

This project reads live measurement data from a Bird 5019 sensor over RS-232 and prints it to the terminal in plain text or JSON.

## Problem

The Bird 5019 exposes useful RF power data over an RS-232 interface, but using that interface on a modern computer is awkward. Most laptops and small PCs no longer include a native serial port, and manually talking to the device protocol is inconvenient for testing, logging, or automation.

## Solution

`bird_5019_serial_read.py` connects to the sensor, identifies it, checks calibration status, applies measurement settings, and then streams live readings such as:

- forward power
- reflected power
- peak power
- burst power
- filter bandwidth
- temperature
- ACK status

It can output human-readable terminal lines for quick monitoring or JSON for scripting and data capture.

## Hardware Requirements

- Bird 5019 or compatible 5012-family sensor
- External 7-18 VDC power for the sensor
- USB to RS-232 converter cable
- Correct RS-232 wiring between the converter and the sensor

Use a real RS-232 converter cable, not a USB-to-TTL serial adapter.

## Software Requirements

- Python 3
- `pyserial`

Install the dependency with:

```bash
python3 -m pip install pyserial
```

## Usage

List available serial ports:

```bash
python3 bird_5019_serial_read.py --list-ports
```

Read continuously from the default detected adapter:

```bash
python3 bird_5019_serial_read.py
```

Read from a specific port:

```bash
python3 bird_5019_serial_read.py --port /dev/ttyUSB0
```

Change the sensor filter bandwidth:

```bash
python3 bird_5019_serial_read.py --port /dev/ttyUSB0 --filter 400k
python3 bird_5019_serial_read.py --port /dev/ttyUSB0 --filter 400khz
python3 bird_5019_serial_read.py --port /dev/ttyUSB0 --filter 10mhz
```

Supported filter values are:

- `4k5`, `4.5khz`, or `4500` for 4.5 kHz
- `400k`, `400khz`, or `400000` for 400 kHz
- `10m`, `10mhz`, or `10000000` for 10 MHz

Read a limited number of samples in JSON format:

```bash
python3 bird_5019_serial_read.py --port /dev/ttyUSB0 --samples 5 --json
```

## Output

Plain-text mode prints one line per sample with:

- timestamp
- forward power
- reflected power
- peak power
- burst power
- filter bandwidth
- temperature
- ACK status

Power values in plain-text mode are formatted with two digits after the decimal point.

JSON mode emits one object per sample with the same measurement data.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

The program was created by using GPT-5.4
