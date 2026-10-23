# WeatherLink Live local HTTP driver for WeeWX

Poll a Davis WeatherLink Live device's local `/v1/current_conditions` HTTP API.
The driver reads weather, barometric and indoor observations, including separate
ISS and wind transmitters. It uses local polling, not WeatherLink cloud access,
UDP real-time broadcasts or historical archive downloads.

Release 0.2.2 is an independent continuation of
[jonotaegi/weewx-wll](https://github.com/jonotaegi/weewx-wll), with explicit
transmitter selection, HTTP timeouts and rain/pressure mapping corrections.

## Install

The catalog release requires Python >=3.10 and WeeWX >=5.2,<6.

Install `requests` in the WeeWX Python environment:

```sh
python -m pip install requests
```

Use the `weectl` from your WeeWX Python environment:

```sh
weectl extension install https://github.com/weewx-packages/weewx-wll/releases/download/v0.2.2/weewx-wll-0.2.2.zip --config=/path/to/weewx.conf
weectl station reconfigure --driver=user.wll --config=/path/to/weewx.conf
```

Replace `/path/to/weewx.conf` with your station configuration. Stock WeeWX 5
accepts this fixed URL or a downloaded copy of the same archive. No catalog
integration is required. Restart WeeWX yourself after configuration changes.

## Configure local polling

```ini
[Station]
    station_type = WLL
[WLL]
    driver = user.wll
    host = 192.0.2.10
    poll_interval = 10
    timeout = 5
    iss_id = 1
    wind_id = 1
```

Replace the address and transmitter IDs. The WeeWX host must reach the WLL on
your LAN. `poll_interval` must be at least 10 seconds. `iss_id` selects the
ISS `txid`; set `wind_id` to a different transmitter for a separate anemometer.
Without explicit IDs, non-null values from all transmitters can combine, so
select them when observations overlap. `wind_id` defaults to `iss_id`.

`dayRain` is the daily counter in inches; the driver calculates packet rain
from its running counters. `bar_sea_level` maps to `altimeter` by default;
`pressure_field = barometer` restores the older mapping. `bar_absolute` maps
to `pressure` in either mode. Extra fields need archive columns to retain them;
current LOOP data alone do not add columns.

Restart WeeWX and inspect its logs. A top-level `loop_on_init = true` lets
WeeWX retry initialization after temporary network failures. This refresh used
no WLL device or separated transmitters. The driver's fixture checks do not
establish radio reception or firmware behavior. See the
[local API documentation](https://weatherlink.github.io/weatherlink-live-local-api/)
for endpoint and discovery background.

Copyright 2020 Jon Otaegi. The driver is GPL-3.0-or-later; `install.py` is
GPL-3.0-only. See [LICENSE](LICENSE), [NOTICE](NOTICE) and source headers.

<!-- Documentation updated 2026-10-23 by weewx-packages. -->
