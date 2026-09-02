# Coal Mine Sensor Simulator

This simulator produces CSV data in the hardware team's agreed format:

```csv
node_id,timestamp,position_x,position_y,tilt_x,tilt_y,vibration_rms,vibration_peak,crack_width
NODE_01,2026-08-30T12:00:00Z,0.0,0.0,0.024,-0.071,0.104,0.177,0.132
```

It uses three patterns: `normal`, `deteriorating` (slow, persistent movement), and `dangerous_event` (rapid vibration and displacement indicators). Values are simulated engineering values; align their units and alert thresholds with the hardware team before operational use.

## Run it

Requires Python 3.10+ and no external packages.

```powershell
python sensor_simulator.py --count 100 --interval 0 --seed 42 --output simulated_readings.csv
```

This generates a CSV file with 100 complete ticks (300 rows with the default three nodes). `--count 0` (the default) streams forever. Leave out `--output` to view the CSV stream in the terminal.

Configure any set of nodes with `--nodes`:

```powershell
python sensor_simulator.py --nodes "NORTH_01,0,0,normal;NORTH_02,30,15,deteriorating;SOUTH_01,80,40,dangerous_event" --count 10
```

The CSV column names are exactly: `node_id`, `timestamp`, `position_x`, `position_y`, `tilt_x`, `tilt_y`, `vibration_rms`, `vibration_peak`, and `crack_width`. The future backend should use these as its CSV ingestion contract.

For direct integration, import `SensorSimulator` and call `readings()` once per collection tick, or iterate over `stream(interval_seconds)`.
