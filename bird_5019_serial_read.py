#!/usr/bin/env python3
import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

import serial
import serial.tools.list_ports


FILTER_HZ = {
    "4k5": 4.5e3,
    "400k": 400e3,
    "10m": 10e6,
}

UNITS = {
    "00": "None",
    "01": "dB",
    "02": "Rho",
    "03": "VSWR",
    "04": "R",
    "05": "RL",
    "06": "dBm",
    "07": "uW",
    "08": "mW",
    "09": "W",
    "0A": "kW",
    "0B": "Auto W",
    "0C": "MHz",
    "0D": "kHz",
}


class BirdSerialError(RuntimeError):
    pass


@dataclass
class Measurement:
    timestamp: str
    forward_power: float
    reflected_power: float
    units: str
    temperature_c: float
    peak_power: float
    burst_power: float
    filter_hz: float
    ack: str


def list_ports() -> list[str]:
    return [p.device for p in serial.tools.list_ports.comports()]


def default_port() -> str:
    ports = list_ports()
    for port in ports:
        if port.startswith("/dev/ttyUSB") or port.startswith("/dev/ttyACM"):
            return port
    raise SystemExit("No serial adapter found. Pass --port explicitly.")


class Bird5012FamilySerialSensor:
    def __init__(self, port: str, baudrate: int = 9600, timeout: float = 2.0) -> None:
        self.port = port
        self.serial = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=8,
            parity="N",
            stopbits=1,
            timeout=timeout,
            xonxoff=False,
            rtscts=False,
            dsrdtr=False,
        )

    def close(self) -> None:
        self.serial.close()

    def _drain(self) -> None:
        time.sleep(0.1)
        self.serial.reset_input_buffer()
        self.serial.reset_output_buffer()

    def _write(self, command: bytes) -> None:
        self.serial.write(command)
        self.serial.flush()

    def _read_until(self, marker: bytes = b"\r\n") -> bytes:
        data = self.serial.read_until(marker)
        if not data:
            raise BirdSerialError(
                "no response from sensor on RS-232; verify the sensor has external 7-18 VDC power, "
                "that the adapter is true RS-232 level, and that TX/RX are wired correctly"
            )
        return data

    def identify(self) -> tuple[str, str]:
        self._drain()
        self._write(b"I\r\n")
        data = self.serial.read_until(b"rs232\r\n")
        if not data:
            self._write(b"I\n")
            data = self.serial.read_until(b"rs232\r\n")
        if not data:
            raise BirdSerialError(
                "no identification response; Bird's RS-232 method requires external 7-18 VDC power"
            )

        text = data.decode("utf-8", errors="ignore")
        parts = text.split(",")
        if len(parts) < 3 or "501" not in parts[0]:
            raise BirdSerialError(f"unexpected identification response: {text!r}")

        model = parts[0].strip()
        fw_date = parts[1].strip()
        fw_and_iface = parts[2].splitlines()
        fw_version = fw_and_iface[0].strip()

        self._write(b"S\r\n")
        serial_resp = self._read_until().decode("utf-8", errors="ignore").rstrip().split(",")
        serial_number = serial_resp[1].strip() if len(serial_resp) > 1 else ""
        return f"{model},{fw_date},{fw_version}", serial_number

    def calibration_status(self) -> tuple[str, str]:
        self._write(b"F\r\n")
        text = self._read_until().decode("utf-8", errors="ignore").rstrip()
        parts = text.split(",")
        if len(parts) < 2:
            raise BirdSerialError(f"unexpected calibration response: {text!r}")
        return parts[0].strip(), parts[1].strip()

    def configure(
        self,
        measurement_type: int = 1,
        offset_db: float = 0.0,
        filter_name: str = "400k",
        units: str = "09",
        ccdf_limit: float = 150.0,
    ) -> tuple[str, str, str]:
        cmd = (
            f"G,0{measurement_type},{offset_db:0.5e},{FILTER_HZ[filter_name]:0.5e},"
            f"{units},{ccdf_limit:0.5e}\r\n"
        ).encode("ascii")
        self._write(cmd)
        text = self._read_until().decode("utf-8", errors="ignore").rstrip()
        parts = text.split(",")
        if len(parts) < 3:
            raise BirdSerialError(f"unexpected configuration response: {text!r}")
        return parts[0].strip(), parts[1].strip(), parts[2].strip()

    def get_one_dataset(self) -> Measurement:
        self._write(b"T\r\n")
        text = self._read_until().decode("utf-8", errors="ignore").rstrip()
        parts = text.split(",")
        if len(parts) < 14:
            raise BirdSerialError(f"unexpected dataset response: {text!r}")

        unit_code = parts[8].strip().upper().zfill(2)
        return Measurement(
            timestamp=datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            forward_power=float(parts[3]),
            reflected_power=float(parts[4]),
            units=UNITS.get(unit_code, unit_code),
            temperature_c=float(parts[2]),
            peak_power=float(parts[5]),
            burst_power=float(parts[1]),
            filter_hz=float(parts[6]),
            ack=parts[13].strip(),
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Read forward and reflected power from a Bird 5019 over RS-232.")
    parser.add_argument("--port", default=None, help="Serial device path, for example /dev/ttyUSB0")
    parser.add_argument("--baud", type=int, default=9600, help="Baud rate")
    parser.add_argument("--timeout", type=float, default=2.0, help="Serial read timeout in seconds")
    parser.add_argument(
        "--samples",
        type=int,
        default=None,
        help="Number of samples to read; omit for continuous output",
    )
    parser.add_argument("--interval", type=float, default=0.35, help="Delay between samples in seconds")
    parser.add_argument("--filter", choices=sorted(FILTER_HZ), default="400k", help="Sensor filter bandwidth")
    parser.add_argument("--json", action="store_true", help="Emit one JSON object per sample")
    parser.add_argument("--list-ports", action="store_true", help="List serial ports and exit")
    args = parser.parse_args()

    if args.list_ports:
        for port in list_ports():
            print(port)
        return 0

    port = args.port or default_port()
    sensor = Bird5012FamilySerialSensor(port=port, baudrate=args.baud, timeout=args.timeout)
    try:
        ident, serial_number = sensor.identify()
        cal_cmd, cal_state = sensor.calibration_status()
        cfg_cmd, cfg_filter, cfg_state = sensor.configure(filter_name=args.filter)

        print(f"sensor={ident},serial={serial_number}")
        print(f"calibration={cal_cmd},{cal_state}")
        print(f"configuration={cfg_cmd},{cfg_filter},{cfg_state}")

        count = 0
        while args.samples is None or count < args.samples:
            sample = sensor.get_one_dataset()
            if args.json:
                print(json.dumps(asdict(sample)), flush=True)
            else:
                print(
                    f"{sample.timestamp} "
                    f"forward={sample.forward_power:.2f} {sample.units} "
                    f"reflected={sample.reflected_power:.2f} {sample.units} "
                    f"peak={sample.peak_power:.2f} {sample.units} "
                    f"burst={sample.burst_power:.2f} {sample.units} "
                    f"filter={sample.filter_hz:.0f} Hz "
                    f"temp={sample.temperature_c:.2f} C "
                    f"ack={sample.ack}",
                    flush=True,
                )
            count += 1
            time.sleep(max(args.interval, 0.0))
    except KeyboardInterrupt:
        return 0
    except BirdSerialError as exc:
        print(f"Serial error: {exc}", file=sys.stderr)
        return 2
    finally:
        sensor.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
