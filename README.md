# Flight Tracker Display

Track live aircraft from major metro areas and display flight details on an [Inky Impression 7.3" e-ink display](https://shop.pimoroni.com/products/inky-impression-7-3) using a Raspberry Pi.

## Features

- Displays flight callsign, airline, origin and destination, altitude, speed, and distance from home.
- Rotates between metro areas (Austin, Dallas/Fort Worth, Houston).
- Fetches airline logos via Clearbit.
- Uses data from [ADSB.lol](https://www.adsb.lol) and [adsbdb.com](https://adsbdb.com).

## Hardware Requirements

- [Inky Impression 7.3" Display](https://shop.pimoroni.com/products/inky-impression-7-3)
- Raspberry Pi 3, 4, or Zero W
- MicroSD card (8GB or more)
- Internet connection (WiFi or Ethernet)
- 5V power supply for Raspberry Pi

## Software Requirements

- Python 3.9+
- Raspberry Pi OS (Lite or Full)
- Dependencies (see `requirements.txt`)

## Setup

1. Clone this repository:

```bash
git clone https://github.com/yourusername/flight_tracker_display.git
cd flight_tracker_display
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the script:

```bash
python flight_tracker.py
```

Make sure to enable I2C and SPI on your Raspberry Pi using `raspi-config`.

## Example Output

Here’s an example of the flight tracker display in action:


![Flight Tracker Example](example.png)


## License

MIT License
