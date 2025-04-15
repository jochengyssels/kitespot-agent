import os
import time
import logging
import requests
from typing import List
from bs4 import BeautifulSoup
from core.supabase_client import supabase
from core.logger import log_agent_action

logger = logging.getLogger("kitespot-image-enrichment")

class KitespotImageEnrichmentAgent:
    def __init__(self):
        self.request_delay = 2.0
        self.max_images = 3

    def _load_all_kitespots(self) -> List[dict]:
        try:
            response = supabase.table("kitespots") \
                .select("id, name, country") \
                .eq("images_enriched", False) \
                .execute()
            return response.data
        except Exception as e:
            logger.error(f"Failed to load kitespots: {str(e)}")
            return []

    def _search_images(self, query: str, limit: int = 3) -> List[str]:
        url = f"https://www.google.com/search?tbm=isch&q={query.replace(' ', '+')}"
        headers = {"User-Agent": "Mozilla/5.0"}
        images = []

        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code != 200:
                return images

            soup = BeautifulSoup(response.text, 'html.parser')
            for img_tag in soup.find_all("img"):
                src = img_tag.get("src")
                if src and src.startswith("http"):
                    images.append(src)
                if len(images) >= limit:
                    break

        except Exception as e:
            logger.error(f"Image search failed for query '{query}': {str(e)}")

        return images

    def _upload_images_to_supabase(self, spot_id: str, image_urls: List[str]) -> List[str]:
        saved_paths = []
        for idx, url in enumerate(image_urls):
            retries = 3
            while retries > 0:
                try:
                    response = requests.get(url, timeout=15)
                    if response.status_code == 200:
                        path = f"kitespots/{spot_id}/image_{idx}.jpg"
                        supabase.storage.from_("kitespot-images").upload(path, response.content, {"content-type": "image/jpeg"})
                        saved_paths.append(path)
                        break
                except Exception as e:
                    logger.error(f"Failed to upload image from {url}: {str(e)}")
                    retries -= 1
                    time.sleep(1)
        return saved_paths


    def _update_kitespot_with_images(self, spot_id: str, image_paths: List[str]):
        try:
            supabase.table("kitespots").update({
                "image_paths": image_paths,
                "images_enriched": True
            }).eq("id", spot_id).execute()
        except Exception as e:
            logger.error(f"Failed to update kitespot {spot_id} with images: {str(e)}")

    def enrich_kitespot_images(self):
        agent_name = "kitespot_image_enrichment"
        log_agent_action(agent_name, "started")

        spots = self._load_all_kitespots()
        enriched_count = 0
        total_images = 0

        for spot in spots:
            query = f"kitesurfing {spot['country']} {spot['name']}"
            image_urls = self._search_images(query, limit=self.max_images)

            if not image_urls:
                continue

            saved_paths = self._upload_images_to_supabase(spot['id'], image_urls)

            if saved_paths:
                self._update_kitespot_with_images(spot['id'], saved_paths)
                enriched_count += 1
                total_images += len(saved_paths)

            time.sleep(self.request_delay)

        log_agent_action(agent_name, "finished", {"enriched_spots": enriched_count, "images_uploaded": total_images})


if __name__ == "__main__":
    agent = KitespotImageEnrichmentAgent()
    agent.enrich_kitespot_images()
