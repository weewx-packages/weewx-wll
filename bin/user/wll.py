#!/usr/bin/env python
# Modified 2026-10-22 by weewx-packages.
# -*- coding: utf-8 -*-
# WeatherLink Live (WLL) driver for WeeWX
#
# Copyright 2020 Jon Otaegi
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.
#
# See http://www.gnu.org/licenses/

""" WeeWX driver for WeatherLink Live (WLL) devices.

The WeatherLink Live (WLL) implements a HTTP interface for getting current weather data. The response is a JSON document with the current weather from all the Davis transmitters it is tracking. The Live’s barometer, inside temperature, and inside humidity are also returned. The interface can support continuous requests as often as every 10 seconds.

https://weatherlink.github.io/weatherlink-live-local-api/

This driver fetches new data from the device and sends it to WeeWX.

"""

from __future__ import with_statement
import time
import requests

import weewx
import weewx.drivers

DRIVER_NAME = 'WLL'
DRIVER_VERSION = '0.2.0'

MM_TO_INCH = 0.0393701

try:
    # WeeWX 4 logging
    import weeutil.logger
    import logging

    log = logging.getLogger(__name__)

    # def logdbg(msg):
    #     log.debug(msg)

    # def loginf(msg):
    #     log.info(msg)

    def logerr(msg):
        log.error(msg)

except ImportError:
    # Old-style WeeWX logging
    import syslog


    def logmsg(level, msg):
        syslog.syslog(level, 'WLL: %s' % msg)

    # def logdbg(msg):
    #     logmsg(syslog.LOG_DEBUG, msg)

    # def loginf(msg):
    #     logmsg(syslog.LOG_INFO, msg)

    def logerr(msg):
        logmsg(syslog.LOG_ERR, msg)


def loader(config_dict, engine):
    return WLL(**config_dict['WLL'])


class WLL(weewx.drivers.AbstractDevice):
    @property
    def default_stanza(self):
        return """
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
"""

    def __init__(self, **stn_dict):

        self.host = stn_dict.get('host')

        if self.host is None:
            raise ValueError("The WeatherLink Live hostname or ip address is required.")

        self.service_url = "http://%s:80/v1/current_conditions" % self.host

        self.poll_interval = float(stn_dict.get('poll_interval', 10))

        if self.poll_interval < 10:
            logerr("The `poll_interval` parameter should be 10 or greater.")

        self.timeout = float(stn_dict.get('timeout', 5))
        self.iss_id = stn_dict.get('iss_id')
        self.wind_id = stn_dict.get('wind_id', self.iss_id)
        self.pressure_field = stn_dict.get('pressure_field', 'altimeter')
        if self.pressure_field not in ('altimeter', 'barometer'):
            raise ValueError('pressure_field must be altimeter or barometer')
        self.hardware = stn_dict.get('hardware')

        self.last_rain_storm = None
        self.last_rain_storm_start_at = None

    @property
    def hardware_name(self):
        return self.hardware

    def genLoopPackets(self):

        while True:

            try:

                try:

                    response = requests.get(self.service_url, timeout=self.timeout)
                    response.raise_for_status()

                except requests.RequestException as exception:

                    logerr("Error connecting to the WeatherLink Live device.")
                    logerr("%s" % exception)

                    time.sleep(2)

                    continue  # Continue without exiting.

                data = response.json()

                timestamp = data['data']['ts']

                _packet = {
                    'dateTime': timestamp,
                    'usUnits': weewx.US
                }

                for condition in data['data']['conditions']:

                    data_structure_type = condition["data_structure_type"]
                    if data_structure_type == 1:
                        txid = str(condition.get('txid'))
                        is_iss = self.iss_id is None or txid == str(self.iss_id)
                        is_wind = self.wind_id is None or txid == str(self.wind_id)
                        # A separate wind transmitter reports null ISS fields.
                        condition = {key: value for key, value in condition.items()
                                     if value is not None and
                                     (is_wind if key.startswith('wind_') else is_iss)}

                    # 1 = ISS Current Conditions record
                    if data_structure_type == 1:

                        if "temp" in condition:  # most recent valid temperature **(°F)**
                            _packet.update({'outTemp': condition["temp"]})

                        if "hum" in condition:  # most recent valid temperature **(°F)**
                            _packet.update({'outHumidity': condition["hum"]})

                        if "dew_point" in condition:  # **(°F)**
                            _packet.update({'dewpoint': condition["dew_point"]})

                        if "heat_index" in condition:  # **(°F)**
                            _packet.update({'heatindex': condition["heat_index"]})

                        if "wind_chill" in condition:  # **(°F)**
                            _packet.update({'windchill': condition["wind_chill"]})

                        if "wind_speed_last" in condition:  # most recent valid wind speed **(mph)**
                            _packet.update({'windSpeed': condition["wind_speed_last"]})

                        if "wind_dir_last" in condition:  # most recent valid wind direction **(°degree)**
                            _packet.update({'windDir': condition["wind_dir_last"]})

                        if "wind_speed_hi_last_10_min" in condition:  # maximum wind speed over last 10 min **(mph)**
                            _packet.update({'windGust': condition["wind_speed_hi_last_10_min"]})

                        if "wind_dir_scalar_avg_last_10_min" in condition:  # gust wind direction over last 10 min **(°degree)**
                            _packet.update({'windGustDir': condition["wind_dir_scalar_avg_last_10_min"]})

                        if "rain_size" in condition:  # rain collector type/size **(0: Reserved, 1: 0.01", 2: 0.2 mm, 3:  0.1 mm, 4: 0.001")**

                            rain_collector_type = condition["rain_size"]

                            if 1 <= rain_collector_type <= 4:

                                if rain_collector_type == 1:
                                    rain_count_size = 0.01

                                elif rain_collector_type == 2:
                                    rain_count_size = 0.2 * MM_TO_INCH

                                elif rain_collector_type == 3:
                                    rain_count_size = 0.1 * MM_TO_INCH

                                elif rain_collector_type == 4:
                                    rain_count_size = 0.001

                                if "rainfall_daily" in condition:
                                    _packet['dayRain'] = float(condition['rainfall_daily']) * rain_count_size

                                if "rain_rate_last" in condition:  # most recent valid rain rate **(counts/hour)**
                                    _packet.update({'rainRate': float(condition["rain_rate_last"]) * rain_count_size})

                                if "rain_storm" in condition and "rain_storm_start_at" in condition:

                                    # Calculate the rain accumulation by reading the total rain count and checking the increments

                                    rain_storm = condition["rain_storm"]  # total rain count since last 24 hour long break in rain **(counts)**
                                    rain_storm_start_at = condition["rain_storm_start_at"]  # UNIX timestamp of current rain storm start **(seconds)**

                                    rain_count = 0.0

                                    if self.last_rain_storm is not None and self.last_rain_storm_start_at is not None:

                                        if rain_storm_start_at != self.last_rain_storm_start_at:
                                            rain_count = rain_storm

                                        elif rain_storm >= self.last_rain_storm:
                                            rain_count = float(rain_storm) - float(self.last_rain_storm)

                                    self.last_rain_storm = rain_storm
                                    self.last_rain_storm_start_at = rain_storm_start_at

                                    _packet.update({'rain': rain_count * rain_count_size})

                        if "solar_rad" in condition:  #
                            _packet.update({'radiation': condition["solar_rad"]})

                        if "uv_index" in condition:  #
                            _packet.update({'UV': condition["uv_index"]})

                        if "trans_battery_flag" in condition:  #
                            _packet.update({'txBatteryStatus': condition["trans_battery_flag"]})

                    # 2 = Leaf/Soil Moisture Current Conditions record
                    elif data_structure_type == 2:

                        if "temp_1" in condition:  # most recent valid soil temp slot 1 **(°F)**
                            _packet.update({'soilTemp1': condition["temp_1"]})

                        if "temp_2" in condition:  # most recent valid soil temp slot 2 **(°F)**
                            _packet.update({'soilTemp2': condition["temp_2"]})

                        if "temp_3" in condition:  # most recent valid soil temp slot 3 **(°F)**
                            _packet.update({'soilTemp3': condition["temp_3"]})

                        if "temp_4" in condition:  # most recent valid soil temp slot 4 **(°F)**
                            _packet.update({'soilTemp4': condition["temp_4"]})

                        if "moist_soil_1" in condition:  # most recent valid soil moisture slot 1 **(|cb|)**
                            _packet.update({'soilMoist1': condition["moist_soil_1"]})

                        if "moist_soil_2" in condition:  # most recent valid soil moisture slot 2 **(|cb|)**
                            _packet.update({'soilMoist2': condition["moist_soil_2"]})

                        if "moist_soil_3" in condition:  # most recent valid soil moisture slot 3 **(|cb|)**
                            _packet.update({'soilMoist3': condition["moist_soil_3"]})

                        if "moist_soil_4" in condition:  # most recent valid soil moisture slot 4 **(|cb|)**
                            _packet.update({'soilMoist4': condition["moist_soil_4"]})

                        if "wet_leaf_1" in condition:  # most recent valid leaf wetness slot 1 **(no unit)**
                            _packet.update({'leafWet1': condition["wet_leaf_1"]})

                        if "wet_leaf_2" in condition:  # most recent valid leaf wetness slot 2 **(no unit)**
                            _packet.update({'leafWet2': condition["wet_leaf_2"]})

                    # 3 = LSS BAR Current Conditions record
                    elif data_structure_type == 3:

                        if "bar_sea_level" in condition:  # most recent bar sensor reading with elevation adjustment **(inches)**
                            _packet.update({self.pressure_field: condition["bar_sea_level"]})

                        if "bar_absolute" in condition:  # raw bar sensor reading **(inches)**
                            _packet.update({'pressure': condition["bar_absolute"]})

                    # 4 = LSS Temp/Hum Current Conditions record
                    elif data_structure_type == 4:

                        if "temp_in" in condition:  # most recent valid inside temp **(°F)**
                            _packet.update({'inTemp': condition["temp_in"]})

                        if "hum_in" in condition:  # most recent valid inside humidity **(%RH)**
                            _packet.update({'inHumidity': condition["hum_in"]})

                        if "dew_point_in" in condition:  # **(°F)**
                            _packet.update({'inDewpoint': condition["dew_point_in"]})

                yield _packet

                time.sleep(self.poll_interval)

            except (ValueError, KeyError, TypeError) as exception:

                logerr("Error parsing the WeatherLink Live json data.")
                logerr("%s" % exception)

                time.sleep(self.poll_interval)

                pass  # Continue without exiting.



