import requests
from bs4 import BeautifulSoup

def fetch_kitespots():
    url = "https://example-kitespots.com"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    spots = []

    for spot in soup.select('.spot'):
        name = spot.select_one('.spot-name').text.strip()
        location = spot.select_one('.spot-location').text.strip()
        latitude = spot.get('data-latitude')
        longitude = spot.get('data-longitude')

        spots.append({
            "name": name,
            "location": location,
            "latitude": latitude,
            "longitude": longitude
        })

    return spots
