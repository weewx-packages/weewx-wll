## weewx-wll

### Installation

1) Download the driver

```
wget -O weewx-wll.zip https://github.com/jonotaegi/weewx-wll/archive/master.zip
```

2) Install the driver

```
sudo wee_extension --install weewx-wll.zip
```

3) Enable the `loop_on_init` parameter, set the `station_type` to `WLL` and modify the `[WLL]` stanza in `weewx.conf`:
```
# If the WLL driver fails to load, unless setting this option to 1, WeeWX will exit.
# The driver can fail to load for intermittent reasons, such as a network failures.
loop_on_init = 1
```
```
[Station]

    # Set the type of station.
    station_type = WLL
```
```
[WLL]
    # This section is for the WeatherLink Live devices.

    # The hostname or ip address of the WeatherLink Live device in the local network.
    # For the driver to work, the WeatherLink Live and the computer running WeeWX have to be on the same local network.
    # For details on programmatically finding WeatherLink Live devices on the local network, see https://weatherlink.github.io/weatherlink-live-local-api/discovery.html
    host = 1.2.3.4

    # How often to poll the weather data (in seconds).
    # The interface can support continuous requests as often as every 10 seconds.
    poll_interval = 10

    # The driver to use:
    driver = user.wll
```

4) Restart WeeWX

```
sudo /etc/init.d/weewx restart
```

Note: The driver requires the Python `requests` library. To install it:

```
sudo apt-get update 
sudo apt-get install python-requests
```
or
```
pip install requests
```
## Independent continuation

This repository continues `jonotaegi/weewx-wll` with its original Git history.
Original authors retain their copyrights. The driver is GPL-3.0-or-later;
`install.py` is GPL-3.0-only. See `LICENSE` and source headers.

Version 0.2.2 supports WeeWX 5 and Python 3.10 through 3.14. Install with:

```
weectl extension install https://github.com/weewx-packages/weewx-wll/archive/refs/tags/v0.2.2.zip
```

Set `host` in `[WLL]`. Optional `timeout` defaults to 5 seconds. To use separate
transmitters, set `iss_id` to the ISS transmitter's `txid`, and `wind_id` to the
anemometer transmitter's `txid`. Without these settings, non-null measurements
from all transmitters are combined. Select explicit IDs if multiple transmitters
report the same measurement.

`dayRain` is the device's daily counter converted to inches. It is available in
LOOP packets without adding an archive database column. `bar_sea_level` maps to
`altimeter` by default. `pressure_field = barometer` retains the previous mapping.
The raw `bar_absolute` value maps to `pressure` in either mode.

Run `python -m pytest -q tests` for HTTP and packet regression tests. Tests use
fixtures and a local HTTP receiver. An actual WLL and separated transmitters
remain necessary to verify radio reception and device firmware behavior.
