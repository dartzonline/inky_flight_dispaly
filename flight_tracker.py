"""
Flight Tracker Display
======================

This script fetches live aircraft data from ADSB.lol and displays
the most relevant flight over a rotating list of metro areas
on an Inky Impression e-ink display.

Flight details include:
- Callsign
- Airline name
- Origin and destination airports
- Altitude, speed, and distance from home

Logos are fetched from Clearbit using airline domains.

Author: Open-source contributor
License: MIT
"""

import logging
import math
import time
import requests
from io import BytesIO
from PIL import Image, ImageFont, ImageDraw
from inky.auto import auto

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Coordinates of your home location (generic default; change for your setup)
HOME_COORDS = (31.0, -97.0)

# Metro areas to scan for aircraft
LOCATIONS = [
    {"name": "Austin", "lat": 30.3, "lon": -97.7, "radius": 50},
    {"name": "Dallas/Fort Worth", "lat": 32.9, "lon": -97.0, "radius": 50},
    {"name": "Houston", "lat": 29.9, "lon": -95.3, "radius": 50},
]

# Known airline domain mappings for logo fetching
AIRLINE_LOGO_DOMAINS = {
    "American Airlines": "aa.com",
    "Delta Air Lines": "delta.com",
    "United Airlines": "united.com",
    "Southwest Airlines": "southwest.com",
    "Alaska Airlines": "alaskaair.com",
    # Add more airlines as needed...
}

# Display and data limits
MAX_AIRCRAFT = 20
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

def haversine(lat1, lon1, lat2, lon2):
    """
    Calculate distance in kilometers between two lat/lon points using Haversine formula.
    """
    R = 6371  # Earth radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def parse_altitude(alt):
    """
    Convert altitude to int safely.
    """
    try:
        return int(alt)
    except (ValueError, TypeError):
        return 0

# Color helper functions
def alt_color(alt): return (int(255 * max(0, min(1, 1 - alt / 40000))), 0, 0)
def dist_color(dist): return (int(255 * max(0, min(1, 1 - dist / 100))), 0, 0)
def speed_color(speed): return (0, int(200 * max(0, min(1, speed / 600))), 0)

class FlightFetcher:
    """
    Fetch aircraft positions and metadata.
    Caches callsign results to reduce API load.
    """
    def __init__(self):
        self.callsign_cache = {}

    def fetch_aircraft(self, lat, lon, radius):
        url = f"https://api.adsb.lol/v2/point/{lat}/{lon}/{radius}"
        try:
            logger.info(f"Fetching aircraft data for lat={lat}, lon={lon}")
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            return resp.json().get("ac", [])[:MAX_AIRCRAFT]
        except Exception as e:
            logger.error(f"Aircraft fetch failed: {e}")
            return []

    def fetch_route_info(self, callsign):
        """
        Fetch airline, origin, and destination by callsign using adsbdb.com.
        """
        if callsign in self.callsign_cache:
            return self.callsign_cache[callsign]

        if not callsign:
            self.callsign_cache[callsign] = ("N/A", "N/A", "N/A")
            return self.callsign_cache[callsign]

        url = f"https://api.adsbdb.com/v0/callsign/{callsign}"
        headers = {"accept": "application/json"}
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            fr = resp.json().get("response", {}).get("flightroute", {})
            airline = fr.get("airline", {}).get("name", "N/A")
            origin = fr.get("origin", {}).get("name", "N/A")
            dest = fr.get("destination", {}).get("name", "N/A")
            self.callsign_cache[callsign] = (airline, origin, dest)
        except Exception as e:
            logger.error(f"Route info fetch failed for {callsign}: {e}")
            self.callsign_cache[callsign] = ("N/A", "N/A", "N/A")

        return self.callsign_cache[callsign]

class FlightDisplay:
    """
    Handles rendering aircraft data to an Inky Impression display.
    """
    def __init__(self, display):
        self.display = display
        try:
            self.font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
            self.font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
            self.font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
        except IOError:
            logger.warning("Default fonts loaded due to font error.")
            self.font_large = self.font_medium = self.font_small = ImageFont.load_default()

    def fetch_logo(self, airline):
        """
        Fetch airline logo via Clearbit.
        """
        domain = AIRLINE_LOGO_DOMAINS.get(airline)
        if not domain:
            return None
        try:
            url = f"https://logo.clearbit.com/{domain}"
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            return Image.open(BytesIO(resp.content)).convert("RGBA")
        except Exception as e:
            logger.warning(f"Logo fetch failed for {airline}: {e}")
            return None

    def draw(self, aircraft, loc_name, home_coords):
        """
        Draw aircraft info on display.
        """
        logger.info(f"Rendering display for {loc_name}")
        width, height = self.display.HEIGHT, self.display.WIDTH
        img = Image.new("RGB", (width, height), WHITE)
        draw = ImageDraw.Draw(img)

        ac = aircraft[0]
        callsign = ac.get("flight", "N/A").strip()
        alt = parse_altitude(ac.get("alt_baro"))
        speed = int(ac.get("gs") or 0)
        lat, lon = ac.get("lat"), ac.get("lon")
        airline, origin, dest = ac.get("airline_name", "N/A"), ac.get("origin_name", "N/A"), ac.get("destination_name", "N/A")
        dist_km = haversine(home_coords[0], home_coords[1], lat, lon) if lat and lon else 0
        dist_mi = dist_km * 0.621371
        speed_mph = speed * 1.15078

        y = 10
        draw.text((10, y), f"{loc_name} Area", fill=BLACK, font=self.font_large)
        y += 40
        draw.text((10, y), f"Flight: {callsign}", fill=BLACK, font=self.font_medium)
        y += 30
        draw.text((10, y), f"Airline: {airline}", fill=BLACK, font=self.font_medium)
        y += 30
        draw.text((10, y), f"Altitude: {alt} ft", fill=alt_color(alt), font=self.font_medium)
        y += 30
        draw.text((10, y), f"Speed: {speed_mph:.0f} mph", fill=speed_color(speed), font=self.font_medium)
        y += 30
        draw.text((10, y), f"Distance: {dist_mi:.1f} mi", fill=dist_color(dist_km), font=self.font_medium)
        y += 35
        draw.text((10, y), f"From: {origin}", fill=BLACK, font=self.font_small)
        y += 25
        draw.text((10, y), f"To: {dest}", fill=BLACK, font=self.font_small)

        logo = self.fetch_logo(airline)
        if logo:
            new_w, new_h = 200, 60
            logo = logo.resize((new_w, new_h), Image.LANCZOS)
            img.paste(logo, (width - new_w - 10, height - new_h - 10), logo)

        self.display.set_image(img.rotate(90, expand=True))
        self.display.show()

class FlightTrackerApp:
    """
    Main application that loops over metro areas and displays flight data.
    """
    def __init__(self):
        self.display = auto(ask_user=True, verbose=True)
        self.fetcher = FlightFetcher()
        self.renderer = FlightDisplay(self.display)
        self.idx = 0
        self.last_switch = time.time()
        self.switch_interval = 300  # 5 minutes

    def run(self):
        """
        Main loop: fetch aircraft data, enrich, render, rotate.
        """
        while True:
            now = time.time()
            if now - self.last_switch >= self.switch_interval:
                self.idx = (self.idx + 1) % len(LOCATIONS)
                self.last_switch = now

            loc = LOCATIONS[self.idx]
            aircraft = self.fetcher.fetch_aircraft(loc["lat"], loc["lon"], loc["radius"])

            enriched_aircraft = []
            for ac in aircraft:
                callsign = (ac.get("flight") or "").strip()
                airline, origin, dest = self.fetcher.fetch_route_info(callsign)
                if airline != "N/A":
                    ac.update({
                        "airline_name": airline,
                        "origin_name": origin,
                        "destination_name": dest
                    })
                    enriched_aircraft.append(ac)

            if enriched_aircraft:
                self.renderer.draw(enriched_aircraft, loc["name"], HOME_COORDS)
            else:
                logger.info("No valid aircraft. Skipping to next metro.")
                self.idx = (self.idx + 1) % len(LOCATIONS)
                self.last_switch = now

            time.sleep(10)

if __name__ == "__main__":
    FlightTrackerApp().run()
