"""
Static HTML scraper.

Fetches static HTML pages using requests and extracts job listings
using an LLM. Designed for custom career pages that do not rely on
client-side JavaScript rendering.
"""

import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup

from src.models.job import Job, ListingType
from src.utils.llm_client import get_llm_client

# Keywords that indicate an internship listing
INTERNSHIP_KEYWORDS = ("intern", "co-op", "coop", "apprentice", "trainee")


def classify_listing_type(title: str) -> ListingType:
    """Classify a job title as internship or job."""
    title_lower = title.lower()
    for keyword in INTERNSHIP_KEYWORDS:
        if keyword in title_lower:
            return ListingType.internship
    return ListingType.job


def extract_company_from_url(url: str) -> str:
    """Extract a fallback company name from a URL."""
    parsed = urlparse(url)
    # Return the domain without www.
    netloc = parsed.netloc
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc.split(".")[0]


def clean_html(html: str) -> str:
    """
    Clean HTML by removing irrelevant tags and extracting text with links.
    """
    soup = BeautifulSoup(html, "lxml")
    
    # Remove irrelevant elements
    for element in soup(["script", "style", "noscript", "svg", "img", "nav", "footer", "header"]):
        element.extract()
        
    # Extract text with link annotations
    lines = []
    for el in soup.find_all(["a", "div", "p", "h1", "h2", "h3", "li", "span"]):
        if el.name == "a" and el.get("href"):
            href = el.get("href")
            text = el.get_text(strip=True)
            if text:
                lines.append(f"{text} [Link: {href}]")
        else:
            text = el.get_text(strip=True)
            if text:
                lines.append(text)
                
    # Join and limit to a reasonable chunk for the LLM
    content = "\n".join(lines)
    # Deduplicate lines loosely
    seen = set()
    final_lines = []
    for line in content.split("\n"):
        if line not in seen:
            seen.add(line)
            final_lines.append(line)
            
    return "\n".join(final_lines)[:10000]


def extract_jobs_with_llm(html_content: str, base_url: str) -> list[Job]:
    """
    Use an LLM to extract job listings from cleaned HTML content.
    """
    cleaned_text = clean_html(html_content)
    
    prompt = f"""
    Extract job listings from this text dump of a career page.
    The base URL of the company is: {base_url}
    
    For each job you find, extract:
    - title: Job title
    - location: Job location (if specified, otherwise empty string)
    - url: The application or detail link (resolve relative links using the base URL)
    
    Respond with ONLY a JSON list of objects.
    Example:
    [
        {{"title": "Software Engineer", "location": "Remote", "url": "https://example.com/jobs/1"}}
    ]
    
    Text dump:
    {cleaned_text}
    """
    
    client = get_llm_client()
    try:
        extracted_data = client.extract(prompt)
    except Exception as e:
        print(f"LLM Extraction failed: {e}")
        return []
        
    if not isinstance(extracted_data, list):
        return []
        
    company_name = extract_company_from_url(base_url)
    jobs = []
    
    for item in extracted_data:
        if not isinstance(item, dict):
            continue
            
        title = item.get("title", "")
        if not title:
            continue
            
        location = item.get("location", "")
        url = item.get("url", "")
        listing_type = classify_listing_type(title)
        
        job = Job(
            title=title[:255],
            company=company_name,
            location=location[:255],
            description="Extracted via Generic Scraper",
            url=url[:500] if url else base_url,
            listing_type=listing_type,
        )
        jobs.append(job)
        
    return jobs


class StaticScraper:
    """Scraper for static custom career pages."""
    
    def __init__(self, url: str):
        self.url = url
        self.company_name = extract_company_from_url(url)
        self.jobs: list[Job] = []
        
    def scrape(self) -> list[Job]:
        """Fetch page and extract jobs."""
        response = requests.get(self.url, timeout=10)
        response.raise_for_status()
        
        self.jobs = extract_jobs_with_llm(response.text, self.url)
        return self.jobs

    def scrape_from_html(self, html: str) -> list[Job]:
        """Parse pre-fetched HTML without network."""
        self.jobs = extract_jobs_with_llm(html, self.url)
        return self.jobs
