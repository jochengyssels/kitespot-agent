import os
import time
import random
import logging
import requests
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from urllib.parse import urlparse, quote_plus
from core.supabase_client import supabase
from core.logger import log_agent_action

logger = logging.getLogger("kiteschool_agent")

class KiteschoolAgent:
    def __init__(self):
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            "Mozilla/5.0 (X11; Linux x86_64)"
        ]
        self.request_delay = 2.0
        self.max_retries = 3

    def _load_kiteschools(self) -> List[Dict]:
        response = supabase.table("kiteschools") \
            .select("id, company_name, country, website") \
            .is_("website", None) \
            .execute()
        return response.data

    def _search_website(self, company_name: str, country: str) -> Optional[str]:
        query = quote_plus(f"{company_name} {country} kitesurfing school official website")
        url = f"https://www.google.com/search?q={query}"
        headers = {"User-Agent": random.choice(self.user_agents)}

        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code != 200:
                return None
            soup = BeautifulSoup(response.text, 'html.parser')
            for link in soup.find_all("a", href=True):
                href = link['href']
                if href.startswith("/url?q="):
                    clean_url = href[7:].split('&')[0]
                    if not any(domain in clean_url for domain in ['facebook', 'instagram', 'tripadvisor']):
                        return clean_url
        except Exception as e:
            logger.error(f"Error searching website for {company_name}: {str(e)}")
        return None

    def _fetch_logo(self, website_url: str, kiteschool_id: str) -> Optional[str]:
        try:
            response = requests.get(website_url, timeout=15)
            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.text, 'html.parser')
            for link in soup.find_all('link', rel=['icon', 'shortcut icon']):
                logo_url = link.get('href')
                if logo_url:
                    if not logo_url.startswith("http"):
                        parsed = urlparse(website_url)
                        logo_url = f"{parsed.scheme}://{parsed.netloc}{logo_url}"

                    img_response = requests.get(logo_url, timeout=15)
                    if img_response.status_code == 200:
                        storage_path = f"kiteschools/{kiteschool_id}/logo.png"
                        supabase.storage.from_("kiteschool-logos").upload(storage_path, img_response.content, {"content-type": "image/png"})
                        return storage_path
        except Exception as e:
            logger.error(f"Error fetching logo for {website_url}: {str(e)}")
        return None

    def _extract_pricing_and_review(self, website_url: str) -> Dict[str, Optional[str]]:
        price_level = None
        review_score = None

        try:
            headers = {"User-Agent": random.choice(self.user_agents)}
            response = requests.get(website_url, headers=headers, timeout=15)
            if response.status_code != 200:
                return {"price_level": price_level, "review_score": review_score}

            soup = BeautifulSoup(response.text, 'html.parser')
            text = soup.get_text().lower()

            if any(x in text for x in ['starting at €', 'from €', 'less than €']):
                price_level = "$"
            elif any(x in text for x in ['starting at €100', '€100 per day', '€150']):
                price_level = "$$"
            elif any(x in text for x in ['€200', '€250', 'premium course']):
                price_level = "$$$"

            review_match = soup.find("span", string=lambda s: s and "review" in s.lower())
            if review_match:
                review_score = review_match.text

        except Exception as e:
            logger.warning(f"Failed to extract pricing or review for {website_url}: {str(e)}")

        return {"price_level": price_level, "review_score": review_score}

    def enrich_kiteschools(self):
        agent_name = "kiteschool_agent"
        log_agent_action(agent_name, "started")

        schools = self._load_kiteschools()
        updated_count = 0

        for school in schools:
            website = self._search_website(school["company_name"], school["country"])
            if not website:
                continue

            logo_path = self._fetch_logo(website, school["id"])
            extra_data = self._extract_pricing_and_review(website)

            data = {"website": website}
            if logo_path:
                data["logo_path"] = logo_path
            if extra_data.get("price_level"):
                data["price_level"] = extra_data["price_level"]
            if extra_data.get("review_score"):
                data["review_score"] = extra_data["review_score"]

            supabase.table("kiteschools").update(data).eq("id", school["id"]).execute()
            updated_count += 1

            time.sleep(self.request_delay)

        log_agent_action(agent_name, "finished", {"updated": updated_count})


if __name__ == "__main__":
    agent = KiteschoolAgent()
    agent.enrich_kiteschools()
