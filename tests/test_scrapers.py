# import pytest
# from unittest.mock import MagicMock, patch
# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker

# from src.config.database import Base
# from src.models.Listing import Job, ListingType
# from src.scrapers.lever_scraper import LeverScraper, save_listings_to_db as save_lever_db
# from src.scrapers.greenhouse_scraper import GreenhouseScraper, save_listings_to_db as save_greenhouse_db


# # --- Mock Classes for Playwright ---
# class MockElement:
#     def __init__(self, inner_text_val, href_val=None, visible=True, enabled=True):
#         self.inner_text_val = inner_text_val
#         self.href_val = href_val
#         self._visible = visible
#         self._enabled = enabled

#     def inner_text(self):
#         return self.inner_text_val

#     def get_attribute(self, name):
#         if name == "href":
#             return self.href_val
#         return None

#     def query_selector(self, selector):
#         if selector in ('[data-qa="posting-name"]', 'h5', 'a'):
#             return MockElement(self.inner_text_val, self.href_val)
#         if selector == '.location':
#             return MockElement("San Francisco")
#         return None

#     def is_visible(self):
#         return self._visible

#     def is_enabled(self):
#         return self._enabled

#     def click(self):
#         pass


# class MockPage:
#     def __init__(self, cards, jd_text=""):
#         self.cards = cards
#         self.jd_text = jd_text
#         self.goto_calls = []

#     def goto(self, url, wait_until=None):
#         self.goto_calls.append(url)

#     def query_selector_all(self, selector):
#         if selector in ('.posting', '.opening'):
#             return self.cards
#         return []

#     def query_selector(self, selector):
#         if selector in ('.posting-sections', '.section', '#content'):
#             return MockElement(self.jd_text)
#         return None

#     def wait_for_load_state(self, state):
#         pass


# class MockBrowser:
#     def __init__(self, page):
#         self.page = page

#     def new_page(self):
#         return self.page

#     def close(self):
#         pass


# class MockPlaywright:
#     def __init__(self, page):
#         self.chromium = MagicMock()
#         self.chromium.launch.return_value = MockBrowser(page)


# # --- Pytest Fixtures ---
# @pytest.fixture(autouse=True)
# def setup_test_db(tmp_path, monkeypatch):
#     db_path = tmp_path / "test_jobs.db"
#     db_url = f"sqlite:///{db_path}"
#     engine = create_engine(db_url, connect_args={"check_same_thread": False})
#     TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
#     Base.metadata.create_all(bind=engine)
    
#     monkeypatch.setattr("src.scrapers.lever_scraper.SessionLocal", TestingSessionLocal)
#     monkeypatch.setattr("src.scrapers.greenhouse_scraper.SessionLocal", TestingSessionLocal)
    
#     yield TestingSessionLocal
    
#     Base.metadata.drop_all(bind=engine)


# @pytest.fixture(autouse=True)
# def mock_sleep():
#     with patch("time.sleep") as mock_s:
#         yield mock_s


# @pytest.fixture
# def mock_lever_pw():
#     cards = [
#         MockElement("Software Engineer", "https://jobs.lever.co/anthropic/uuid1"),
#         MockElement("Software Engineer Intern", "https://jobs.lever.co/anthropic/uuid2"),
#         MockElement("Research Intern", "https://jobs.lever.co/anthropic/uuid3"),
#     ]
#     page = MockPage(cards, jd_text="Detailed Lever description.")
#     pw = MockPlaywright(page)
    
#     with patch("src.scrapers.lever_scraper.sync_playwright") as mock_sync:
#         mock_sync.return_value.__enter__.return_value = pw
#         yield page, cards


# @pytest.fixture
# def mock_greenhouse_pw():
#     cards = [
#         MockElement("Software Engineer", "/notion/jobs/uuid1"),
#         MockElement("Intern - QA", "/notion/jobs/uuid2"),
#         MockElement("Product Manager Co-op", "/notion/jobs/uuid3"),
#     ]
#     page = MockPage(cards, jd_text="Detailed Greenhouse description.")
#     pw = MockPlaywright(page)
    
#     with patch("src.scrapers.greenhouse_scraper.sync_playwright") as mock_sync:
#         mock_sync.return_value.__enter__.return_value = pw
#         yield page, cards


# # --- Lever Scraper Tests ---
# def test_lever_scraper_basic(mock_lever_pw):
#     scraper = LeverScraper()
#     listings = scraper.scrape("https://jobs.lever.co/anthropic")
    
#     assert len(listings) == 3
#     assert listings[0]["company_name"] == "anthropic"
#     assert listings[0]["role_title"] == "Software Engineer"
#     assert listings[0]["location"] == "San Francisco"
#     assert listings[0]["listing_type"] == "job"
#     assert listings[0]["jd_text"] == "Detailed Lever description."
#     assert listings[1]["role_title"] == "Software Engineer Intern"
#     assert listings[1]["listing_type"] == "internship"


# def test_lever_scraper_modes(mock_lever_pw):
#     scraper = LeverScraper()
    
#     # job mode
#     jobs = scraper.scrape("https://jobs.lever.co/anthropic", mode="job")
#     assert len(jobs) == 1
#     assert jobs[0]["role_title"] == "Software Engineer"
    
#     # internship mode
#     internships = scraper.scrape("https://jobs.lever.co/anthropic", mode="internship")
#     assert len(internships) == 2
#     assert internships[0]["role_title"] == "Software Engineer Intern"
#     assert internships[1]["role_title"] == "Research Intern"


# def test_lever_scraper_db_save(mock_lever_pw, setup_test_db):
#     scraper = LeverScraper()
#     listings = scraper.scrape("https://jobs.lever.co/anthropic")
    
#     saved_count = save_lever_db(listings)
#     assert saved_count == 3
    
#     db = setup_test_db()
#     jobs = db.query(Job).all()
#     assert len(jobs) == 3
#     assert jobs[0].company == "anthropic"
#     assert jobs[0].title == "Software Engineer"
#     assert jobs[1].listing_type == ListingType.internship
    
#     # Duplicate save (updates fields instead of inserting new)
#     listings[0]["role_title"] = "Updated Software Engineer"
#     save_lever_db(listings)
#     db.expire_all()
#     jobs_after = db.query(Job).all()
#     assert len(jobs_after) == 3
#     updated_job = db.query(Job).filter(Job.url == listings[0]["application_url"]).first()
#     assert updated_job.title == "Updated Software Engineer"
#     db.close()


# # --- Greenhouse Scraper Tests ---
# def test_greenhouse_scraper_basic(mock_greenhouse_pw):
#     scraper = GreenhouseScraper()
#     listings = scraper.scrape("https://boards.greenhouse.io/notion")
    
#     assert len(listings) == 3
#     assert listings[0]["company_name"] == "notion"
#     assert listings[0]["role_title"] == "Software Engineer"
#     assert listings[0]["location"] == "San Francisco"
#     assert listings[0]["listing_type"] == "job"
#     assert listings[0]["jd_text"] == "Detailed Greenhouse description."
#     assert listings[0]["application_url"] == "https://boards.greenhouse.io/notion/jobs/uuid1"
    
#     assert listings[1]["role_title"] == "Intern - QA"
#     assert listings[1]["listing_type"] == "internship"


# def test_greenhouse_scraper_modes(mock_greenhouse_pw):
#     scraper = GreenhouseScraper()
    
#     jobs = scraper.scrape("https://boards.greenhouse.io/notion", mode="job")
#     assert len(jobs) == 1
#     assert jobs[0]["role_title"] == "Software Engineer"
    
#     internships = scraper.scrape("https://boards.greenhouse.io/notion", mode="internship")
#     assert len(internships) == 2
#     assert internships[0]["role_title"] == "Intern - QA"
#     assert internships[1]["role_title"] == "Product Manager Co-op"


# def test_greenhouse_scraper_db_save(mock_greenhouse_pw, setup_test_db):
#     scraper = GreenhouseScraper()
#     listings = scraper.scrape("https://boards.greenhouse.io/notion")
    
#     saved_count = save_greenhouse_db(listings)
#     assert saved_count == 3
    
#     db = setup_test_db()
#     jobs = db.query(Job).all()
#     assert len(jobs) == 3
#     assert jobs[0].company == "notion"
#     assert jobs[1].listing_type == ListingType.internship
#     db.close()

from src.scrapers.lever_scraper import lever
from src.scrapers.greenhouse_scraper import greenhouse
from src.models.Listing import Listing
import pytest

@pytest.fixture(scope="module")
def lever_jobs():
    scraper = lever(
        "employ",
        "https://jobs.lever.co/employ"
    )
    return scraper.scrape()

def test_jobs(lever_jobs):
    jobs = lever_jobs
    assert isinstance(jobs , list )
    assert len(jobs) > 0 
    for job in jobs : 
        assert isinstance(job , Listing)
        assert job.role_title
        assert job.company_name
        assert job.application_url.startswith("http")
        assert job.jd_text
        assert job.source in ["lever", "greenhouse"]

def test_save_to_db(lever_jobs):
    from src.models import Base
    from src.config.database import engine
    
    # Create tables for the test database
    Base.metadata.create_all(bind=engine)
    
    jobs = lever_jobs
    from src.scrapers.db_utils import save_listings_to_db
    try:
        saved_count = save_listings_to_db(jobs)
        assert saved_count == len(jobs)
        print(saved_count)
    finally:
        # Clean up after the test
        Base.metadata.drop_all(bind=engine)




# def test_greenhouse_returns_list(): 
if __name__ == "__main__":
    pytest.main([__file__])


# def test_listing_schema(): 

# def test_no_empty_fields(): 

# def test_valid_urls(): 
# def test_listing_type_detection(): 
# def test_source_field(): 
# def test_scraper_handles_empty_page(): 
# def test_scraper_does_not_crash_on_missing_fields():
