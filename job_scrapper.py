import time
import random
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import logging

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from app import app, db
from app import Job, JobApplication  # Make sure these are correctly imported

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0 Safari/537.36'
}

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument(f"user-agent={HEADERS['User-Agent']}")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    return driver

# Global set to track all scraped job links
all_scraped_links = set()

def fetch_cruise_jobs():
    logger.info("🔍 Fetching Cruise Ship Jobs (Indeed)...")
    url = 'https://www.indeed.com/jobs?q=Cruise+Ship&l='
    driver = get_driver()
    added = 0

    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.job_seen_beacon")))
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        job_cards = soup.find_all('div', class_='job_seen_beacon')

        for card in job_cards:
            title_elem = card.find('h2')
            company_elem = card.find('span', class_='companyName')
            link_elem = card.find('a', href=True)

            if title_elem and company_elem and link_elem:
                title = title_elem.text.strip()
                company = company_elem.text.strip()
                link = 'https://www.indeed.com' + link_elem['href']

                all_scraped_links.add(link)

                exists = Job.query.filter_by(link=link).first()
                if not exists:
                    new_job = Job(
                        title=title,
                        company=company,
                        location='Various',
                        industry='Hospitality / Tourism',
                        location_type='Onsite',
                        link=link,
                        posted_date=datetime.utcnow(),
                        expiry_days=30
                    )
                    db.session.add(new_job)
                    added += 1
        db.session.commit()
        logger.info(f"✅ Cruise Jobs Added: {added}")
    except Exception as e:
        logger.error(f"Error fetching cruise jobs: {e}")
    finally:
        driver.quit()

def fetch_remote_jobs():
    logger.info("🔍 Fetching Remote Tech Jobs (RemoteOK)...")
    url = 'https://remoteok.com/remote-python-jobs'
    driver = get_driver()
    added = 0

    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "tr.job")))
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        job_posts = soup.select('tr.job')

        for job in job_posts:
            title = job.find('h2')
            company = job.find('h3')
            link = job.get('data-href')

            if title and company and link:
                full_link = f"https://remoteok.com{link}"
                all_scraped_links.add(full_link)

                exists = Job.query.filter_by(link=full_link).first()
                if not exists:
                    new_job = Job(
                        title=title.text.strip(),
                        company=company.text.strip(),
                        location='Remote',
                        industry='IT',
                        location_type='Remote',
                        link=full_link,
                        posted_date=datetime.utcnow(),
                        expiry_days=30
                    )
                    db.session.add(new_job)
                    added += 1
        db.session.commit()
        logger.info(f"✅ RemoteOK Jobs Added: {added}")
    except Exception as e:
        logger.error(f"Error fetching remote jobs: {e}")
    finally:
        driver.quit()

def fetch_remotive_jobs():
    logger.info("🔍 Fetching Remote Tech Jobs (Remotive API)...")
    url = 'https://remotive.io/api/remote-jobs?category=software-dev'
    added = 0

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            logger.error(f"Remotive returned status {response.status_code}")
            return

        data = response.json()
        jobs = data.get('jobs', [])

        for job in jobs:
            title = job.get('title', '').strip()
            company = job.get('company_name', '').strip()
            location = job.get('candidate_required_location', 'Remote').strip()
            link = job.get('url', '').strip()
            description = job.get('description', '').strip()
            industry = 'IT'
            location_type = 'Remote' if 'remote' in location.lower() else 'Onsite'

            # Try extracting email from description (optional and error-prone)
            import re
            email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', description)
            email = email_match.group(0) if email_match else None

            if title and company and link:
                all_scraped_links.add(link)
                exists = Job.query.filter_by(link=link).first()
                if not exists:
                    new_job = Job(
                        title=title,
                        company=company,
                        location=location,
                        industry=industry,
                        location_type=location_type,
                        link=link,
                        email=email,  # Add email here
                        description=description,
                        posted_date=datetime.utcnow(),
                        expiry_days=30
                    )
                    db.session.add(new_job)
                    added += 1
        db.session.commit()
        logger.info(f"✅ Remotive API Jobs Added: {added}")
    except Exception as e:
        logger.error(f"Error fetching Remotive API Jobs: {e}")

def fetch_craigslist_jobs():
    logger.info("🔍 Fetching Craigslist Jobs...")
    base_url = "https://newyork.craigslist.org/search/sof"  # Example for NYC Software Jobs
    driver = get_driver()
    added = 0

    try:
        driver.get(base_url)
        WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".result-info")))

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        listings = soup.select(".result-info")

        for post in listings:
            title_elem = post.find("a", class_="result-title")
            date_elem = post.find("time")
            link = title_elem['href'] if title_elem else None

            if link:
                driver.get(link)
                time.sleep(2)
                page_soup = BeautifulSoup(driver.page_source, 'html.parser')
                description = page_soup.find("section", id="postingbody").get_text(strip=True)
                title = page_soup.find("span", id="titletextonly").text.strip()
                email_elem = page_soup.select_one("a.mailapp")

                email = email_elem.text if email_elem else None
                company = "Craigslist Poster"

                if not Job.query.filter_by(link=link).first():
                    job = Job(
                        title=title,
                        company=company,
                        location="USA",
                        industry="IT",
                        location_type="Remote" if "remote" in description.lower() else "Onsite",
                        link=link,
                        email=email,
                        description=description[:500],
                        posted_date=datetime.utcnow(),
                        expiry_days=30
                    )
                    db.session.add(job)
                    added += 1

        db.session.commit()
        logger.info(f"✅ Craigslist Jobs Added: {added}")
    except Exception as e:
        logger.error(f"❌ Error fetching Craigslist jobs: {e}")
    finally:
        driver.quit()


def fetch_concentrix_jobs():
    logger.info("🔍 Fetching Concentrix Jobs (API)...")
    base_url = "https://apply.concentrix.com/api/content/search-results"
    offset = 0
    limit = 20
    added = 0

    try:
        while True:
            url = f"{base_url}?locale=en_global&offset={offset}&limit={limit}"
            res = requests.get(url, headers=HEADERS)

            if res.status_code != 200:
                logger.error(f"❌ Failed to fetch at offset {offset}: {res.status_code}")
                break

            data = res.json()
            job_cards = data.get('jobPostings', [])

            if not job_cards:
                break  # No more jobs

            for job in job_cards:
                title = job.get('title')
                location = job.get('location') or "Various"
                link = "https://apply.concentrix.com" + job.get('externalPath', '')
                company = "Concentrix"
                industry = job.get('category', 'BPO')
                location_type = 'Remote' if 'Remote' in location else 'Onsite'

                all_scraped_links.add(link)

                if not Job.query.filter_by(link=link).first():
                    new_job = Job(
                        title=title,
                        company=company,
                        location=location,
                        industry=industry,
                        location_type=location_type,
                        link=link,
                        posted_date=datetime.utcnow(),
                        expiry_days=30
                    )
                    db.session.add(new_job)
                    added += 1

            offset += limit
            time.sleep(0.5)

        db.session.commit()
        logger.info(f"✅ Concentrix Jobs Added: {added}")

    except Exception as e:
        logger.error(f"❌ Error fetching Concentrix jobs: {e}")

def fetch_nhs_jobs():
    logger.info("🔍 Fetching NHS Jobs (Selenium)...")
    base_url = "https://www.jobs.nhs.uk/candidate/search/results?keyword=Nurse&location=Birmingham&distance=5&language=en"
    driver = get_driver()
    added = 0
    collected_links = set()

    try:
        driver.get(base_url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a.nhsuk-link--no-visited-state"))
        )

        while True:
            jobs = driver.find_elements(By.CSS_SELECTOR, "a.nhsuk-link--no-visited-state")
            logger.info(f"🔎 Jobs found on page: {len(jobs)}")
            for job in jobs:
                job_url = job.get_attribute("href")
                if job_url and job_url not in collected_links:
                    collected_links.add(job_url)
                    logger.debug(f"✅ Collected job link: {job_url}")

            next_buttons = driver.find_elements(By.CSS_SELECTOR, ".pagination__next a")
            if next_buttons and next_buttons[0].is_enabled():
                next_buttons[0].click()
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a.nhsuk-link--no-visited-state"))
                )
            else:
                break

        logger.info(f"ℹ️ NHS links collected: {len(collected_links)}")

        for link in collected_links:
            try:
                driver.get(link)
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "vacancy-header")))

                title = driver.find_element(By.CSS_SELECTOR, "h1.vacancy-header__title").text.strip()
                company = driver.find_element(By.CSS_SELECTOR, "dl.vacancy-details dd").text.strip()
                location = driver.find_element(By.XPATH, "//dt[text()='Location']/following-sibling::dd").text.strip()
                description_elem = driver.find_elements(By.CSS_SELECTOR, ".vacancy-description")
                description = description_elem[0].text.strip() if description_elem else "No description available"

                all_scraped_links.add(link)

                if not Job.query.filter_by(link=link).first():
                    job = Job(
                        title=title,
                        company=company,
                        location=location,
                        country='UK',
                        industry='Healthcare',
                        location_type='Onsite',
                        link=link,
                        description=description[:500],
                        posted_date=datetime.utcnow(),
                        expiry_days=30
                    )
                    db.session.add(job)
                    added += 1
            except Exception as e:
                logger.error(f"❌ Error processing NHS job {link}: {e}")

        db.session.commit()
    except Exception as e:
        logger.error(f"❌ Error during NHS job fetching: {e}")
    finally:
        driver.quit()

    logger.info(f"✅ NHS Jobs Added: {added}")

def delete_expired_jobs():
    expiry_threshold = datetime.utcnow() - timedelta(days=30)
    expired_jobs = Job.query.filter(Job.posted_date < expiry_threshold).all()
    for job in expired_jobs:
        logger.info(f"🗑️ Deleting expired job: {job.title} at {job.company}")
        db.session.delete(job)
    db.session.commit()

def delete_jobs_not_found():
    expiry_threshold = datetime.utcnow() - timedelta(days=7)
    stale_jobs = Job.query.filter(
        ~Job.link.in_(all_scraped_links),
        Job.posted_date < expiry_threshold
    ).all()
    for job in stale_jobs:
        logger.info(f"🗑️ Deleting stale job (not found in scrape): {job.title} at {job.company}")
        db.session.delete(job)
    db.session.commit()

def run_all_scrapers():
    with app.app_context():
        fetch_remote_jobs()
        time.sleep(random.uniform(1.5, 3.0))

        fetch_nhs_jobs()
        time.sleep(random.uniform(1.5, 3.0))

        fetch_cruise_jobs()
        time.sleep(random.uniform(1.5, 3.0))

        fetch_remotive_jobs()
        time.sleep(random.uniform(1.5, 3.0))

        fetch_concentrix_jobs()
        time.sleep(random.uniform(1.5, 3.0))

        fetch_craigslist_jobs()

        delete_expired_jobs()
        delete_jobs_not_found()

        logger.info("✅✅✅ All scrapers completed.")

if __name__ == "__main__":
    run_all_scrapers()
