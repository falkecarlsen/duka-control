# duka controller
ESPHome powered control of whitelabel HRU-units from [Vents TwinFresh Comfo](https://ventilation-system.com/series/twinfresh-comfo-ra1-85-v3/) but purchased as [Duka One C6](https://dukaventilation.dk/produkter/1-rums-ventilationsloesninger/duka-one-c6).

The aim is to actuate with control strategies from metrics gathered for the home. High temperature and humidity outdoor? Only exhaust from the basement to take drier air from upstrais. Low demand as specified by CO2, humidity, or radon? Run heat-recovery in low fan-mode to retain more heat.

The units are provided with a remote that decoded initially showed promise, but later abandoned in favour of directly hooking into the provided (undocumented) bus. 
It consists of D (5V), GND and is meant for series-connection of multiple units to balance the airflow in heat-recovery mode.

A bitpattern of max 56ms is repeated every ~99ms. A pulse seems to be 1.65ms long, allowing for a bitvector length of 34 bits. All unique states measured are provided raw in traces/ for reference. The heat-recovery unit switches between \*-in.csv and \*-out.csv every ~70s.


