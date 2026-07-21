from playwright.sync_api import sync_playwright

from src.models.Listing import Listing , ListingType
from src.scrapers.db_utils import save_listings_to_db as save_listings_to_db_shared


# class LeverScraper:
#     RATE_DELAY = 1.0

#     def scrape(self, board_url: str, mode: str = "all") -> list[dict]:
#         listings = []
#         with sync_playwright() as p:
#             browser = p.chromium.launch(headless=True)
#             page = browser.new_page()
#             page.goto(board_url, wait_until='networkidle')

#             company_name = board_url.rstrip("/").split("/")[-1]

#             temp_listings = []
#             while True:
#                 cards = page.query_selector_all('.posting')
#                 for card in cards:
#                     parsed = self._parse_card(card, company_name)
#                     if parsed:
#                         temp_listings.append(parsed)

#                 # Check for next page
#                 next_btn = page.query_selector('a.next, a.next-page, button.next, a:has-text("Next")')
#                 if next_btn and next_btn.is_visible() and next_btn.is_enabled():
#                     next_btn.click()
#                     page.wait_for_load_state('networkidle')
#                     time.sleep(self.RATE_DELAY)
#                 else:
#                     break

#             # Visit detail pages to get descriptions
#             for item in temp_listings:
#                 page.goto(item["application_url"], wait_until='networkidle')
#                 section_el = page.query_selector('.posting-sections') or page.query_selector('.section')
#                 if section_el:
#                     item["jd_text"] = section_el.inner_text().strip()
#                 else:
#                     body_el = page.query_selector('body')
#                     item["jd_text"] = body_el.inner_text().strip() if body_el else ""

#                 item["posting_date"] = None
#                 listings.append(item)
#                 time.sleep(self.RATE_DELAY)

#             browser.close()

#         # Filter by mode
#         return [l for l in listings if self._mode_matches(l, mode)]

#     def _parse_card(self, card, company_name: str) -> dict | None:
#         title_el = card.query_selector('[data-qa="posting-name"]') or card.query_selector('h5')
#         if not title_el:
#             return None
#         title = title_el.inner_text().strip()

#         location_el = card.query_selector('.location')
#         location = location_el.inner_text().strip() if location_el else ""

#         link_el = card.query_selector('a')
#         if not link_el:
#             return None
#         app_url = link_el.get_attribute('href')
#         if not app_url:
#             return None

#         # Resolve relative links
#         if app_url.startswith("/"):
#             app_url = "https://jobs.lever.co" + app_url
#         elif not app_url.startswith("http"):
#             app_url = "https://jobs.lever.co/" + app_url

#         ltype = self._get_listing_type(title)

#         return {
#             "company_name": company_name,
#             "role_title": title,
#             "location": location,
#             "application_url": app_url,
#             "listing_type": ltype,
#         }

#     def _get_listing_type(self, title: str) -> str:
#         title_lower = title.lower()
#         internship_keywords = ["intern", "co-op", "stage", "placement", "trainee", "apprenticeship"]
#         if any(keyword in title_lower for keyword in internship_keywords):
#             return "internship"
#         return "job"

#     def _mode_matches(self, listing: dict, mode: str) -> bool:
#         if mode == "all":
#             return True
#         return listing["listing_type"] == mode


# def save_listings_to_db(listings: list[dict]) -> int:
#     db = SessionLocal()
#     saved_count = 0
#     try:
#         for item in listings:
#             ltype = ListingType.internship if item["listing_type"] == "internship" else ListingType.job
#             existing = db.query(Job).filter(Job.url == item["application_url"]).first()
#             if existing:
#                 existing.title = item["role_title"]
#                 existing.company = item["company_name"]
#                 existing.location = item["location"]
#                 existing.description = item["jd_text"]
#                 existing.listing_type = ltype
#             else:
#                 job = Job(
#                     title=item["role_title"],
#                     company=item["company_name"],
#                     location=item["location"],
#                     description=item["jd_text"],
#                     url=item["application_url"],
#                     listing_type=ltype,
#                 )
#                 db.add(job)
#             saved_count += 1
#         db.commit()
#     finally:
#         db.close()
#     return saved_count


# if __name__ == "__main__":
#     parser = argparse.ArgumentParser(description="Lever Job Scraper")
#     parser.add_argument("--url", required=True, help="Lever company jobs page URL")
#     parser.add_argument("--mode", default="all", choices=["job", "internship", "all"], help="Scraping mode")
#     args = parser.parse_args()

#     print(f"Scraping Lever board: {args.url} with mode: {args.mode}")
#     scraper = LeverScraper()
#     listings = scraper.scrape(args.url, args.mode)
#     print(f"Extracted {len(listings)} listings.")
    
#     saved = save_listings_to_db(listings)
#     print(f"Saved {saved} jobs to database.")

import time



class lever : 
    def __init__(self , company_name , url) :
        self.company_name = company_name
        self.url = url 
        self.listings = []

    def scrape(self ) :


        last_request = 0
        with sync_playwright() as p : 
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            try : 

                page.goto(self.url)
                jobs = page.locator(".posting")
                jobs_count = jobs.count()
                for i in range(jobs_count): 
                    job = jobs.nth(i)
                    title = job.locator("h5").inner_text()

                    location = job.locator(".sort-by-location").inner_text()
                    application_url = job.locator("a.posting-title").get_attribute("href")
                    # print(title)
                    # print(location)
                    # print(application_url)
                    detail_page = context.new_page()
                    
                    elapsed = time.time() - last_request
                    if elapsed < 1:
                        time.sleep(1 - elapsed)
                        
                    detail_page.goto(application_url)
                    last_request = time.time()
                    
                    jd_text = detail_page.locator('.section-wrapper.page-full-width').nth(2).inner_text()
                    # print("=="*90)
                    # print(jd_text)
                    listing_type = ListingType.internship if "intern" in title.lower() else ListingType.job
                    listing = Listing(
                        company_name= self.company_name,
                        role_title=title,
                        jd_text=jd_text,
                        location=location,
                        application_url=application_url,
                        listing_type=listing_type,
                        source="lever"
                    )
                    self.listings.append(listing)
                    detail_page.close()
                print(self.listings)
            finally : 
                detail_page.close()

        return self.listings


def save_listings_to_db(listings: list[Listing | dict]) -> int:
    return save_listings_to_db_shared(listings, default_source="lever")

if __name__ == "__main__":
    ex = lever(company_name="Employ", url="https://jobs.lever.co/employ")
    saved = save_listings_to_db(ex.scrape())
    print(f"Saved {saved} listings to database.")