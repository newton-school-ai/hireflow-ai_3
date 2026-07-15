from playwright.sync_api import sync_playwright

from src.models.Listing import Listing, ListingType
from src.scrapers.db_utils import save_listings_to_db as save_listings_to_db_shared


# class GreenhouseScraper:
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
#                 cards = page.query_selector_all('.opening')
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
#                 content_el = page.query_selector('#content')
#                 if content_el:
#                     item["jd_text"] = content_el.inner_text().strip()
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
#         link_el = card.query_selector('a')
#         if not link_el:
#             return None
#         title = link_el.inner_text().strip()
#         href = link_el.get_attribute('href')
#         if not href:
#             return None

#         # Resolve relative links
#         app_url = href
#         if href.startswith("/"):
#             app_url = "https://boards.greenhouse.io" + href
#         elif not href.startswith("http"):
#             app_url = "https://boards.greenhouse.io/" + href

#         location_el = card.query_selector('.location')
#         location = location_el.inner_text().strip() if location_el else ""

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
#     parser = argparse.ArgumentParser(description="Greenhouse Job Scraper")
#     parser.add_argument("--url", required=True, help="Greenhouse company jobs board URL")
#     parser.add_argument("--mode", default="all", choices=["job", "internship", "all"], help="Scraping mode")
#     args = parser.parse_args()

#     print(f"Scraping Greenhouse board: {args.url} with mode: {args.mode}")
#     scraper = GreenhouseScraper()
#     listings = scraper.scrape(args.url, args.mode)
#     print(f"Extracted {len(listings)} listings.")
    
#     saved = save_listings_to_db(listings)
#     print(f"Saved {saved} jobs to database.")

import time

class greenhouse:
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
                
                while True:
                    jobs = page.locator("tr.job-post")
                    jobs_count = jobs.count()
                    for i in range(jobs_count): 
                        job = jobs.nth(i)
                        title = job.locator(".body--medium").inner_text()
    
                        location = job.locator(".body__secondary").inner_text()
                        application_url = job.locator("a").get_attribute("href")
                        # print(title)
                        # print(location)
                        # print(application_url)
                        detail_page = context.new_page()
                        
                        elapsed = time.time() - last_request
                        if elapsed < 1:
                            time.sleep(1 - elapsed)
                            
                        detail_page.goto(application_url)
                        last_request = time.time()
                        
                        detail_page.wait_for_selector(".job__description")
    
                        jd_text = detail_page.locator(".job__description").inner_text()
                        # print("=="*90)
                        # print(jd_text[0:100])  # Print first 100 characters of the job description
                        listing_type = ListingType.internship if "intern" in title.lower() else ListingType.job
                        listing = Listing(
                            company_name= self.company_name,
                            role_title=title,
                            jd_text=jd_text,
                            location=location,
                            application_url=application_url,
                            listing_type=listing_type,
                            source="greenhouse"
                        )
                        self.listings.append(listing)
                        detail_page.close()
                    print(f"Scraped {len(self.listings)} listings so far.")
                    
                    if self.has_next_page(page):
                        self.goto_next_page(page)
                    else:
                        break
            finally : 
                detail_page.close()

        return self.listings
    def has_next_page(self,page) -> bool :
        next_button = page.locator(".pagination__next")
        classes = next_button.get_attribute("class")
        return "pagination__next--inactive" not in classes
    def goto_next_page(self,page) : 
        page.locator(".pagination__next").click()

        page.wait_for_load_state("networkidle")
def save_listings_to_db(listings: list[Listing | dict]) -> int:
    return save_listings_to_db_shared(listings, default_source="greenhouse")

if __name__ == "__main__":
    ex = greenhouse(company_name="Employ", url="https://job-boards.greenhouse.io/anthropic")
    saved = save_listings_to_db(ex.scrape())
    print(f"Saved {saved} listings to database.")