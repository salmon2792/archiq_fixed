"""
Job Scraper - Direct internet search, no paid APIs
Scrapes: LinkedIn Jobs, Indeed, Glassdoor public pages, company career pages
Handles rate limiting, retries, and extraction automatically
"""
import asyncio
import httpx
import re
import json
import uuid
from datetime import datetime
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from ai_engine.ontology import ARCH_KEYWORDS, DOMAIN_ONTOLOGY, TARGET_COMPANIES
from ai_engine.engine import extract_skills_from_text

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}

ARCH_QUERIES = [
    "computer architecture engineer",
    "performance engineer CPU",
    "embedded systems engineer",
    "SoC design engineer",
    "VLSI verification engineer",
    "silicon validation engineer",
    "RISC-V engineer",
    "AI accelerator engineer",
    "hardware engineer PMU",
    "post silicon validation engineer",
    "architecture validation engineer",
    "benchmarking engineer embedded",
    "AMBA AXI protocol engineer",
    "BIST DFT engineer",
    "microarchitecture engineer",
]


async def scrape_indeed(query: str, location: str = "", client: httpx.AsyncClient = None) -> List[Dict]:
    """Scrape Indeed job listings"""
    jobs = []
    try:
        encoded_query = query.replace(" ", "+")
        url = f"https://www.indeed.com/jobs?q={encoded_query}&sort=date&limit=15"
        if location:
            url += f"&l={location.replace(' ', '+')}"

        response = await client.get(url, headers=HEADERS, follow_redirects=True, timeout=20)
        if response.status_code != 200:
            return jobs

        soup = BeautifulSoup(response.text, "html.parser")
        job_cards = soup.find_all("div", class_=re.compile(r"job_seen_beacon|jobCard|tapItem"))[:10]

        for card in job_cards:
            try:
                title_el = card.find(["h2", "a"], class_=re.compile(r"jobTitle|title"))
                company_el = card.find(["span", "div"], class_=re.compile(r"companyName|company"))
                location_el = card.find(["div", "span"], class_=re.compile(r"companyLocation|location"))
                summary_el = card.find(["div", "ul"], class_=re.compile(r"job-snippet|summary|underShelfFooter"))

                title = title_el.get_text(strip=True) if title_el else ""
                company = company_el.get_text(strip=True) if company_el else ""
                loc = location_el.get_text(strip=True) if location_el else ""
                summary = summary_el.get_text(strip=True) if summary_el else ""

                link_el = card.find("a", href=True)
                job_url = ""
                if link_el:
                    href = link_el["href"]
                    if href.startswith("/"):
                        job_url = "https://www.indeed.com" + href
                    else:
                        job_url = href

                if title and is_arch_relevant(title + " " + summary):
                    jobs.append({
                        "id": str(uuid.uuid4()),
                        "title": clean_text(title),
                        "company": clean_text(company),
                        "location": clean_text(loc),
                        "jd_text": summary,
                        "source_url": job_url,
                        "source": "indeed",
                        "job_type": "full-time",
                        "fetched_at": datetime.utcnow().isoformat()
                    })
            except Exception:
                continue

    except Exception as e:
        print(f"Indeed scrape error for '{query}': {e}")

    return jobs


async def scrape_linkedin(query: str, client: httpx.AsyncClient = None) -> List[Dict]:
    """Scrape LinkedIn public job search (no login required)"""
    jobs = []
    try:
        encoded = query.replace(" ", "%20")
        url = f"https://www.linkedin.com/jobs/search/?keywords={encoded}&sortBy=DD&f_TPR=r86400"

        response = await client.get(url, headers=HEADERS, follow_redirects=True, timeout=20)
        if response.status_code != 200:
            return jobs

        soup = BeautifulSoup(response.text, "html.parser")
        job_cards = soup.find_all("div", class_=re.compile(r"base-card|job-search-card"))[:10]

        for card in job_cards:
            try:
                title_el = card.find(["h3", "a"], class_=re.compile(r"base-search-card__title|job-card-list__title"))
                company_el = card.find(["h4", "a"], class_=re.compile(r"base-search-card__subtitle|job-card-container__company"))
                location_el = card.find("span", class_=re.compile(r"job-search-card__location"))
                link_el = card.find("a", href=True, class_=re.compile(r"base-card__full-link|job-card-list__title"))

                title = title_el.get_text(strip=True) if title_el else ""
                company = company_el.get_text(strip=True) if company_el else ""
                loc = location_el.get_text(strip=True) if location_el else ""
                job_url = link_el["href"] if link_el else ""

                if title and is_arch_relevant(title):
                    jobs.append({
                        "id": str(uuid.uuid4()),
                        "title": clean_text(title),
                        "company": clean_text(company),
                        "location": clean_text(loc),
                        "jd_text": f"{title} at {company}",
                        "source_url": job_url.split("?")[0] if job_url else "",
                        "source": "linkedin",
                        "job_type": "full-time",
                        "fetched_at": datetime.utcnow().isoformat()
                    })
            except Exception:
                continue

    except Exception as e:
        print(f"LinkedIn scrape error for '{query}': {e}")

    return jobs


async def scrape_wellfound(query: str, client: httpx.AsyncClient = None) -> List[Dict]:
    """Scrape Wellfound (formerly AngelList) for startup jobs"""
    jobs = []
    try:
        encoded = query.replace(" ", "%20")
        url = f"https://wellfound.com/jobs?q={encoded}"

        response = await client.get(url, headers=HEADERS, follow_redirects=True, timeout=20)
        if response.status_code != 200:
            return jobs

        soup = BeautifulSoup(response.text, "html.parser")
        cards = soup.find_all("div", class_=re.compile(r"styles_component|JobListingCard"))[:8]

        for card in cards:
            try:
                title_el = card.find(["h2", "span"], class_=re.compile(r"title|jobTitle|heading"))
                company_el = card.find(["span", "div"], class_=re.compile(r"company|startup"))

                title = title_el.get_text(strip=True) if title_el else card.get_text(strip=True)[:60]
                company = company_el.get_text(strip=True) if company_el else ""
                link_el = card.find("a", href=True)
                href = link_el["href"] if link_el else ""
                job_url = f"https://wellfound.com{href}" if href.startswith("/") else href

                if title and len(title) > 5 and is_arch_relevant(title):
                    jobs.append({
                        "id": str(uuid.uuid4()),
                        "title": clean_text(title[:100]),
                        "company": clean_text(company),
                        "location": "Remote / Startup",
                        "jd_text": f"{title} at {company}",
                        "source_url": job_url,
                        "source": "wellfound",
                        "job_type": "startup",
                        "fetched_at": datetime.utcnow().isoformat()
                    })
            except Exception:
                continue

    except Exception as e:
        print(f"Wellfound scrape error: {e}")

    return jobs


async def scrape_company_careers(company: Dict, client: httpx.AsyncClient = None) -> List[Dict]:
    """Scrape a specific company's career page"""
    jobs = []
    try:
        url = company["careers_url"]
        response = await client.get(url, headers=HEADERS, follow_redirects=True, timeout=20)
        if response.status_code != 200:
            return jobs

        soup = BeautifulSoup(response.text, "html.parser")
        links = soup.find_all("a", href=True)

        for link in links:
            title = link.get_text(strip=True)
            if len(title) > 10 and len(title) < 100 and is_arch_relevant(title):
                href = link["href"]
                job_url = f"https://{url.split('/')[2]}{href}" if href.startswith("/") else href
                jobs.append({
                    "id": str(uuid.uuid4()),
                    "title": clean_text(title),
                    "company": company["name"],
                    "location": "See job posting",
                    "jd_text": title,
                    "source_url": job_url,
                    "source": "company_career",
                    "job_type": "full-time",
                    "fetched_at": datetime.utcnow().isoformat()
                })

        jobs = jobs[:5]

    except Exception as e:
        print(f"Company career scrape error {company['name']}: {e}")

    return jobs


async def fetch_job_details(job: Dict, client: httpx.AsyncClient) -> Dict:
    """Fetch full JD for a job listing"""
    if not job.get("source_url") or len(job.get("jd_text", "")) > 500:
        return job

    try:
        response = await client.get(
            job["source_url"], headers=HEADERS, follow_redirects=True, timeout=15
        )
        if response.status_code != 200:
            return job

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove nav, header, footer noise
        for tag in soup.find_all(["nav", "header", "footer", "script", "style"]):
            tag.decompose()

        # Try to find the main job description area
        jd_el = (
            soup.find("div", id=re.compile(r"job.*desc|description|jobDescription", re.I)) or
            soup.find("div", class_=re.compile(r"job.*desc|description|jobDetails|content", re.I)) or
            soup.find("article") or
            soup.find("main")
        )

        if jd_el:
            text = clean_text(jd_el.get_text(separator=" ", strip=True))[:3000]
            job["jd_text"] = text

    except Exception:
        pass

    return job


def is_arch_relevant(text: str) -> bool:
    """Check if a job posting is relevant to hardware/arch/embedded engineering"""
    text_lower = text.lower()
    keyword_lower = [k.lower() for k in ARCH_KEYWORDS]
    return any(k in text_lower for k in keyword_lower)


def clean_text(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()


def enrich_job_with_skills(job: Dict) -> Dict:
    """Extract skills from job description"""
    jd = job.get("jd_text", "") + " " + job.get("title", "")
    extracted = extract_skills_from_text(jd)
    job["skills_json"] = json.dumps([s["skill_id"] for s in extracted])
    job["skills_detail"] = extracted
    return job


async def run_full_scrape(
    user_query: Optional[str] = None,
    progress_callback=None
) -> List[Dict]:
    """
    Run full scrape across all sources
    Returns deduplicated list of jobs with skills extracted
    """
    all_jobs = []
    seen_urls = set()
    queries = ARCH_QUERIES[:6] if not user_query else [user_query] + ARCH_QUERIES[:3]

    async with httpx.AsyncClient(
        timeout=30,
        limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        follow_redirects=True
    ) as client:

        # Phase 1: Indeed (most reliable)
        if progress_callback:
            await progress_callback("Searching Indeed...", 10)

        indeed_tasks = [scrape_indeed(q, client=client) for q in queries[:4]]
        indeed_results = await asyncio.gather(*indeed_tasks, return_exceptions=True)
        for result in indeed_results:
            if isinstance(result, list):
                all_jobs.extend(result)

        await asyncio.sleep(1)

        # Phase 2: LinkedIn
        if progress_callback:
            await progress_callback("Searching LinkedIn...", 30)

        linkedin_tasks = [scrape_linkedin(q, client=client) for q in queries[:3]]
        linkedin_results = await asyncio.gather(*linkedin_tasks, return_exceptions=True)
        for result in linkedin_results:
            if isinstance(result, list):
                all_jobs.extend(result)

        await asyncio.sleep(1)

        # Phase 3: Wellfound (startups)
        if progress_callback:
            await progress_callback("Searching Wellfound (startups)...", 50)

        wf_jobs = await scrape_wellfound("hardware engineer embedded", client=client)
        all_jobs.extend(wf_jobs)

        await asyncio.sleep(1)

        # Phase 4: Company career pages
        if progress_callback:
            await progress_callback("Checking company career pages...", 65)

        company_tasks = [scrape_company_careers(c, client=client) for c in TARGET_COMPANIES[:5]]
        company_results = await asyncio.gather(*company_tasks, return_exceptions=True)
        for result in company_results:
            if isinstance(result, list):
                all_jobs.extend(result)

        # Phase 5: Deduplicate
        unique_jobs = []
        for job in all_jobs:
            url = job.get("source_url", "")
            key = url or f"{job['title']}-{job['company']}"
            if key not in seen_urls and job.get("title"):
                seen_urls.add(key)
                unique_jobs.append(job)

        # Phase 6: Fetch JD details for top jobs
        if progress_callback:
            await progress_callback("Fetching job details...", 80)

        detail_tasks = [fetch_job_details(j, client) for j in unique_jobs[:20]]
        detailed = await asyncio.gather(*detail_tasks, return_exceptions=True)
        unique_jobs[:20] = [j for j in detailed if isinstance(j, dict)]

    # Phase 7: Extract skills
    if progress_callback:
        await progress_callback("Extracting technical skills from job postings...", 90)

    enriched = [enrich_job_with_skills(j) for j in unique_jobs]

    if progress_callback:
        await progress_callback("Done!", 100)

    print(f"✅ Scraped {len(enriched)} unique jobs")
    return enriched
