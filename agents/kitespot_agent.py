import asyncio
import logging
import json
import time
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup
from geopy.geocoders import Nominatim
import re
from dataclasses import dataclass
import requests
from core.supabase_client import supabase
from core.logger import log_agent_action
import random

# Logging config
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("kitespot-discovery")

class UserAgent:
    @property
    def random(self):
        return random.choice([
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            "Mozilla/5.0 (X11; Linux x86_64)",
        ])

@dataclass
class KitespotInfo:
    name: str
    country: str
    latitude: float
    longitude: float
    description: Optional[str] = None
    difficulty: Optional[str] = None
    best_months: Optional[List[str]] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class KitespotDiscoveryCrawler:
    def __init__(self):
        self.geolocator = Nominatim(user_agent="kitespot_discovery")
        self.user_agent = UserAgent()
        self.request_delay = 2.0
        self.existing_spots_cache = set()
        self.discovery_sources = {
            "windfinder": {
                "url": "https://www.windfinder.com/spots/kitesurfing",
                "parser": self._parse_windfinder
            }
        }

    def _normalize_key(self, name: str, country: str) -> str:
        return re.sub(r'[^a-z0-9]', '', f"{name}_{country}".lower())

    def _spot_exists(self, name: str, country: str) -> bool:
        return self._normalize_key(name, country) in self.existing_spots_cache

    def _load_existing_spots(self):
        try:
            response = supabase.table("kitespots").select("name, country").execute()
            for spot in response.data:
                self.existing_spots_cache.add(self._normalize_key(spot['name'], spot['country']))
            logger.info(f"Loaded {len(self.existing_spots_cache)} existing kitespots")
        except Exception as e:
            logger.error(f"Failed to load existing spots: {str(e)}")

    def _load_all_countries(self) -> List[str]:
        try:
            response = supabase.table("countries").select("name").execute()
            return [country['name'] for country in response.data]
        except Exception as e:
            logger.error(f"Failed to load countries: {str(e)}")
            return []

    def _search_country_kitespots(self, country: str) -> List[KitespotInfo]:
        spots = []
        query = f"{country} kitesurfing spots"
        url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        logger.info(f"Searching for kitespots in {country}")

        try:
            headers = {"User-Agent": self.user_agent.random}
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code != 200:
                return spots

            soup = BeautifulSoup(response.text, 'html.parser')
            text = soup.get_text()

            potential_spots = re.findall(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', text)
            unique_spots = list(set(potential_spots))

            for name in unique_spots:
                if len(name) < 3:
                    continue
                spot = KitespotInfo(
                    name=name.strip(),
                    country=country,
                    latitude=None,
                    longitude=None,
                    source="google_search",
                    source_url=url
                )
                spots.append(spot)

        except Exception as e:
            logger.error(f"Failed country search for {country}: {str(e)}")

        logger.info(f"Found {len(spots)} potential spots in {country}")
        return spots

    def _parse_windfinder(self, html: str, source_url: str) -> List[KitespotInfo]:
        soup = BeautifulSoup(html, 'html.parser')
        spots = []

        links = soup.find_all('a', href=True)
        for link in links:
            href = link['href']
            if '/spots/' in href:
                region_url = f"https://www.windfinder.com{href}"
                spots += self._crawl_region(region_url)

        logger.info(f"Parsed {len(spots)} spots from Windfinder")
        return spots

    def _crawl_region(self, url: str) -> List[KitespotInfo]:
        spots = []
        try:
            headers = {"User-Agent": self.user_agent.random}
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code != 200:
                return spots

            soup = BeautifulSoup(response.text, 'html.parser')
            links = soup.find_all('a', href=True)

            for link in links:
                href = link['href']
                if '/forecast/' in href and link.text.strip():
                    name = link.text.strip()
                    spot = KitespotInfo(
                        name=name,
                        country="",
                        latitude=None,
                        longitude=None,
                        source="windfinder",
                        source_url=url
                    )
                    spots.append(spot)
        except Exception as e:
            logger.error(f"Failed to crawl region {url}: {str(e)}")

        return spots

    def _geocode(self, spot: KitespotInfo) -> Optional[KitespotInfo]:
        try:
            location = self.geolocator.geocode(f"{spot.name} kitesurfing")
            if location:
                spot.latitude = location.latitude
                spot.longitude = location.longitude
                return spot
        except Exception as e:
            logger.warning(f"Geocoding failed for {spot.name}: {e}")
        return None

    def _to_record(self, spot: KitespotInfo) -> dict:
        return {
            "name": spot.name,
            "country": spot.country,
            "latitude": spot.latitude,
            "longitude": spot.longitude,
            "description": spot.description,
            "difficulty": spot.difficulty,
            "best_months": json.dumps(spot.best_months) if spot.best_months else None,
            "source": spot.source,
            "source_url": spot.source_url,
            "metadata": json.dumps(spot.metadata) if spot.metadata else None
        }

    def _save_spots(self, spots: List[KitespotInfo]) -> int:
        new_spots = [self._to_record(s) for s in spots if not self._spot_exists(s.name, s.country) and s.latitude and s.longitude]
        if not new_spots:
            logger.info("No new spots to insert.")
            return 0

        try:
            response = supabase.table("kitespots").insert(new_spots).execute()
            if response.data:
                logger.info(f"Inserted {len(response.data)} new kitespots.")
                return len(response.data)
        except Exception as e:
            logger.error(f"Error inserting new kitespots: {str(e)}")

        return 0

    async def discover_kitespots(self, test_mode: bool = False) -> int:
        agent_name = "kitespot_discovery"
        log_agent_action(agent_name, "started")

        self._load_existing_spots()
        discovered: List[KitespotInfo] = []

        for source_name, source in self.discovery_sources.items():
            try:
                headers = {"User-Agent": self.user_agent.random}
                response = requests.get(source["url"], headers=headers, timeout=15)
                if response.status_code == 200:
                    html = response.text
                    raw_spots = source["parser"](html, source["url"])
                    for spot in raw_spots:
                        enriched = self._geocode(spot)
                        if enriched:
                            discovered.append(enriched)
                        time.sleep(self.request_delay)
                else:
                    logger.warning(f"Failed to fetch {source['url']} (status: {response.status_code})")
            except Exception as e:
                logger.error(f"Error crawling {source_name}: {e}")

        countries = self._load_all_countries()
        for country in countries:
            raw_spots = self._search_country_kitespots(country)
            for spot in raw_spots:
                enriched = self._geocode(spot)
                if enriched:
                    discovered.append(enriched)
                time.sleep(self.request_delay)

        if not discovered:
            logger.warning("No spots discovered from live sources. Using fallback.")
            discovered = self._parse_fallback()

        if test_mode:
            logger.info(f"[TEST MODE] Would insert {len(discovered)} spots")
            log_agent_action(agent_name, "finished", {"test_mode": True, "discovered_count": len(discovered)})
            return len(discovered)

        inserted = self._save_spots(discovered)
        log_agent_action(agent_name, "finished", {"inserted": inserted})
        return inserted


if __name__ == "__main__":
    crawler = KitespotDiscoveryCrawler()
    asyncio.run(crawler.discover_kitespots(test_mode=True))
import logging
import uuid
from datetime import datetime
from core.supabase_client import supabase

logger = logging.getLogger("agent")

def log_agent_action(agent_name: str, status: str, metadata: dict = None):
    try:
        payload = {
            "id": str(uuid.uuid4()),
            "agent_name": agent_name,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        logger.info(f"[{agent_name}] {status} — {metadata}")
        supabase.table("agent_logs").insert(payload).execute()
    except Exception as e:
        logger.error(f"Failed to log agent action: {e}")
