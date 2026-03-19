# AGENTS.md

This repository contains a small Python CLI for reading a Bird 5019 / 5012-family RF power sensor over RS-232.

## Project Scope

- Keep the project simple: one script, minimal dependencies, terminal-first workflow.
- Prefer small, explicit changes over abstractions or framework-style refactors.
- Preserve compatibility with Python 3 and `pyserial`.

## Repository Layout

- `bird_5019_serial_read.py`: main CLI and protocol implementation
- `README.md`: user-facing setup and usage instructions
- `LICENSE`: MIT license

## Hardware And Protocol Facts

- The sensor requires external 7-18 VDC power.
- A true USB-to-RS-232 converter is required. Do not assume a USB-to-TTL adapter will work.
- The serial settings are `9600 8N1` with command termination `\r\n`.
- This project is built around Bird 5000-series / 5012-family RS-232 behavior.
- Current code reads identification, calibration state, configuration acknowledgment, and measurement datasets.

## Important Guardrails

- Do not invent undocumented sensor features.
- Do not add an operating-frequency input unless an official Bird document or Bird GitHub example clearly shows the command and payload format.
- Treat Bird’s public GitHub repo and Bird support documentation as the primary sources for protocol changes.
- If Bird docs and sample code disagree on a protocol detail, prefer the current known-working behavior unless hardware validation is available.

## Current CLI Behavior

- Plain-text mode prints:
  - timestamp
  - forward power
  - reflected power
  - peak power
  - burst power
  - filter value
  - temperature
  - ACK status
- JSON mode emits the `Measurement` dataclass as one JSON object per sample.
- Power values in non-JSON mode are formatted with two decimal places.

## Editing Guidance

- Keep dependencies limited to the standard library plus `pyserial`.
- Keep serial error messages practical and hardware-oriented.
- Preserve the current command-line flags unless there is a clear reason to change them.
- If output fields change, update `README.md` to match.
- If README image links are edited, verify the referenced image file actually exists in the repository.

## Validation

- After code changes, run:

```bash
python3 -m py_compile bird_5019_serial_read.py
```

- If hardware is not connected, say so explicitly rather than implying live-device validation.

## Known Boundaries

- The current implementation does not support setting operating frequency.
- Support for any new Bird command should be backed by an official Bird source or confirmed hardware testing.
