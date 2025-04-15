import requests
from bs4 import BeautifulSoup
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_kitespots():
    url = "https://example-kitespots.com"

    logger.info(f"Fetching kitespots from {url}")

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Request failed: {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')

    spots = []

    for spot in soup.select('.spot'):
        name = spot.select_one('.spot-name')
        location = spot.select_one('.spot-location')
        latitude = spot.get('data-latitude')
        longitude = spot.get('data-longitude')

        if not name or not latitude or not longitude:
            logger.warning("Skipping invalid spot due to missing data")
            continue

        spot_data = {
            "name": name.text.strip(),
            "location": location.text.strip() if location else None,
            "latitude": float(latitude),
            "longitude": float(longitude),
            "source_url": url  # Optional for tracking
        }

        spots.append(spot_data)

    logger.info(f"Fetched {len(spots)} valid kitespots.")

    return spots
