# WeatherLink Live

A WeeWX driver that polls the local `/v1/current_conditions` HTTP API of a
Davis WeatherLink Live (WLL). It reads ISS, leaf/soil, barometer and indoor
records, including separate ISS and wind transmitters. It does not use the
WeatherLink cloud, the UDP real-time broadcast or historical archive downloads.

This is an independent continuation of
[jonotaegi/weewx-wll](https://github.com/jonotaegi/weewx-wll). See
[NOTICE](NOTICE).

## Requirements

- A WeatherLink Live on the local network. The WeeWX host must reach it over
  HTTP on port 80.
- The Python package `requests`, installed in the Python environment that runs
  WeeWX:

  ```sh
  python -m pip install 'requests>=2,<3'
  ```

  Run this with the `python` of the WeeWX virtual environment. For an
  OS-packaged WeeWX, install the distribution package for `requests` instead.

## Installation

Install `wll` from the [WeeWX packages catalog](https://github.com/weewx-packages/catalog/blob/main/packages/wll.md).
The catalog page lists the current release, its WeeWX and Python
requirements, and the install, update and removal commands.

Then select the driver and restart WeeWX:

```sh
weectl station reconfigure --driver=user.wll --config=/path/to/weewx.conf
```

## Configuration

```ini
[Station]
    station_type = WLL

[WLL]
    driver = user.wll
    host = 192.0.2.10
```

Options in `[WLL]`:

| Option | Default | Meaning |
|---|---|---|
| `host` | none, required | Hostname or IP address of the WLL. The installer writes `1.2.3.4`. |
| `poll_interval` | `10` | Seconds between requests. Values below 10 are used, but log an error. |
| `timeout` | `5` | HTTP timeout in seconds. After a failed request the driver logs the error and retries after 2 seconds. |
| `iss_id` | none | `txid` of the ISS transmitter. Without it, records from all transmitters are merged. |
| `wind_id` | value of `iss_id` | `txid` of a separate wind transmitter. All `wind_*` fields except `wind_chill` come from this transmitter. |
| `pressure_field` | `altimeter` | WeeWX field for `bar_sea_level`: `altimeter` or `barometer`. |
| `hardware` | none | Hardware name the driver reports to WeeWX. |

Without `iss_id` and `wind_id`, every transmitter contributes its non-null
values and a later record overwrites an earlier one. Set both when several
transmitters report the same fields.

`windchill` comes from the `iss_id` transmitter. The WLL computes wind chill
only on a transmitter that has both the thermometer and the anemometer. With
a separate wind transmitter, the ISS record carries wind chill only when the
wind import into the ISS is enabled on WeatherLink.com. Otherwise the driver
sets no `windchill`, and with the default `windchill = prefer_hardware` in
`[StdWXCalculate]` WeeWX calculates it.

The WLL reports in US units. `bar_absolute` always maps to `pressure`.
`dayRain` comes from the daily rain counter. Packet `rain` is the increase of
the storm counter between two polls, so the first packet after a start reports
no rain. Rain fields are only set for the collector sizes 0.01 in, 0.2 mm,
0.1 mm and 0.001 in.

The `wview_extended` schema has an archive column for every field the driver
writes. With another schema, fields without a column are not stored.

A top-level `loop_on_init = true` in `weewx.conf` lets WeeWX retry the driver
start after a network failure. The
[local API documentation](https://weatherlink.github.io/weatherlink-live-local-api/)
describes the endpoint and device discovery.

## Limitations

- Tested only against recorded API responses and a local test server, not
  against a WLL device or separate transmitters. Radio reception and firmware
  behaviour are not covered.
- Archives recorded with the original driver differ in three fields. It
  stored `bar_sea_level` as `barometer`; `pressure_field = barometer` keeps
  that mapping. It converted rain from the 0.1 mm and 0.001 in collectors
  with wrong factors. It took `windGustDir` from the 10-minute average
  direction instead of the direction at the peak speed.

## Development

```sh
python -m pytest -q tests
```

## License

Copyright 2020 Jon Otaegi. The driver is GPL-3.0-or-later, `install.py` is
GPL-3.0-only. See [LICENSE](LICENSE), [NOTICE](NOTICE) and the source headers.
