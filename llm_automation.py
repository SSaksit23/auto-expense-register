"""
LLM-Driven Tour Charge Automation
This script provides a step-by-step automation that can be monitored and controlled.
"""

import csv
import time
import re
import logging
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright, expect

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('automation.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
CONFIG = {
    'username': 'noi',
    'password': 'PrayuthChanocha112',
    'login_url': 'https://www.qualityb2bpackage.com/',
    'charges_url': 'https://www.qualityb2bpackage.com/charges_group/create',
    'tour_program_url': 'https://www.qualityb2bpackage.com/travelpackage',
    'description': 'ค่าอุปกรณ์ออกทัวร์',
    'charge_type': 'ค่าอุปกรณ์ออกทัวร์',
    'csv_path': r'C:\Users\saksi\order-bot-automation\tour_data.csv'
}


def get_payment_date():
    """Calculate payment date (today + 7 days)"""
    return (datetime.now() + timedelta(days=7)).strftime("%d/%m/%Y")


def load_csv_data(csv_path, start=0, limit=None):
    """Load tour data from CSV"""
    entries = []
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i < start:
                continue
            if limit and len(entries) >= limit:
                break
            entries.append({
                'tour_code': row['รหัสทัวร์'].strip(),
                'pax': int(row['จำนวนลูกค้า หัก หนท.'].strip()),
                'amount': int(row['ยอดเบิก'].strip())
            })
    return entries


def login(page):
    """Login to the system"""
    logger.info("Logging in...")
    page.goto(CONFIG['login_url'])
    page.wait_for_load_state('domcontentloaded')
    time.sleep(2)
    
    # Fill username and password
    page.locator('input[placeholder*="Username"], input[type="text"]').first.fill(CONFIG['username'])
    page.locator('input[placeholder*="Password"], input[type="password"]').first.fill(CONFIG['password'])
    
    # Click Login button
    page.locator('button:has-text("Login")').click()
    page.wait_for_load_state('domcontentloaded')
    time.sleep(3)
    logger.info("✅ Logged in successfully")


def find_program_code(page, tour_code):
    """Find program code by searching in tour program list"""
    logger.info(f"🔍 Searching for program code: {tour_code}")
    
    page.goto(CONFIG['tour_program_url'])
    page.wait_for_load_state('domcontentloaded')
    time.sleep(2)
    
    # Find search box - using the placeholder text
    search_box = page.locator('input[placeholder*="keyword"], input[placeholder*="ชื่อโปรแกรม"], input[placeholder*="รหัสทัวร์"]').first
    if search_box.count() == 0:
        # Fallback to visible form-control
        search_box = page.locator('input.form-control:visible').last
    
    search_box.fill(tour_code)
    
    # Click Go! button
    search_btn = page.locator('button:has-text("Go!"), button:has-text("ค้นหา")').first
    search_btn.click()
    page.wait_for_load_state('domcontentloaded')
    time.sleep(3)
    
    # Look for program code in the page
    content = page.content()
    
    # Extract prefix from tour code (e.g., 2UCKG from 2UCKG4NCKGFD251206)
    prefix_match = re.match(r'^([A-Z0-9]+?)(\d+N)', tour_code)
    prefix = prefix_match.group(1) if prefix_match else tour_code[:5]
    
    # Find program code pattern (e.g., 2UCKG-FD002)
    pattern = rf'{prefix}-[A-Z]{{2}}\d{{3}}'
    matches = re.findall(pattern, content)
    
    if matches:
        logger.info(f"✅ Found program code: {matches[0]}")
        return matches[0]
    
    # Try alternative pattern without numbers at end
    pattern2 = rf'{prefix}-[A-Z]{{2,4}}\d*'
    matches2 = re.findall(pattern2, content)
    if matches2:
        logger.info(f"✅ Found program code (alt): {matches2[0]}")
        return matches2[0]
    
    logger.warning(f"⚠️ Program code not found for {tour_code}")
    return None


def fill_charge_form(page, tour_code, program_code, amount):
    """Fill the charge creation form using direct UI interactions"""
    logger.info(f"📝 Filling form: {tour_code} | {program_code} | {amount}")
    
    page.goto(CONFIG['charges_url'])
    page.wait_for_load_state('domcontentloaded')
    time.sleep(3)
    
    try:
        # Step 1: Click first date input and change it
        start_date = page.locator('input.form-control').first
        start_date.click()
        time.sleep(0.3)
        
        # Navigate to older month and select date
        # Click previous button multiple times to get to 2024
        for _ in range(24):  # Go back ~2 years
            prev_btn = page.locator('table .prev, .datepicker .prev').first
            if prev_btn.count() > 0:
                prev_btn.click()
                time.sleep(0.1)
        
        # Click first day
        day_cell = page.locator('td.day:not(.old):not(.new)').first
        if day_cell.count() > 0:
            day_cell.click()
        time.sleep(0.5)
        
        # Close any datepicker
        page.keyboard.press('Escape')
        time.sleep(0.5)
        
        # Step 2: Click program dropdown and search
        program_btn = page.locator('button.dropdown-toggle').first
        program_btn.click()
        time.sleep(0.5)
        
        # Type in search
        search_box = page.locator('.bs-searchbox input, input[type="search"]').first
        if search_box.count() > 0 and search_box.is_visible():
            search_box.fill(program_code)
            time.sleep(0.5)
        
        # Click the matching option
        option = page.locator(f'a span:has-text("{program_code}"), li a:has-text("{program_code}")').first
        if option.count() > 0:
            option.click()
        time.sleep(1)
        
        # Step 3: Select Tour Code
        tour_btn = page.locator('button.dropdown-toggle').nth(1)
        tour_btn.click()
        time.sleep(0.5)
        
        tour_option = page.locator(f'a span:has-text("{tour_code}"), li a:has-text("{tour_code}")').first
        if tour_option.count() > 0:
            tour_option.click()
        time.sleep(0.5)
        
        # Step 4-7: Fill remaining fields using JavaScript
        payment_date = get_payment_date()
        page.evaluate(f'''() => {{
            // Fill payment date
            const dateInput = document.querySelector('input[name="date_pay"]');
            if (dateInput) {{
                dateInput.value = '{payment_date}';
                dateInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }}
            
            // Fill description
            const descInput = document.querySelector('input[name="charges_d[description][]"]');
            if (descInput) {{
                descInput.value = '{CONFIG["description"]}';
            }}
            
            // Select type
            const typeSelect = document.querySelector('select[name="charges_d[type][]"]');
            if (typeSelect) {{
                for (let opt of typeSelect.options) {{
                    if (opt.text === '{CONFIG["charge_type"]}') {{
                        typeSelect.value = opt.value;
                        break;
                    }}
                }}
            }}
            
            // Fill amount
            const amountInput = document.querySelector('input[name="charges_d[amount][]"]');
            if (amountInput) {{
                amountInput.value = '{amount}';
            }}
        }}''')
        time.sleep(0.5)
        
        # Step 8: Click Save
        save_btn = page.locator('button:has-text("Save"), input[type="submit"][value="Save"]').first
        save_btn.click()
        page.wait_for_load_state('domcontentloaded')
        time.sleep(3)
        
        logger.info(f"✅ Form submitted for {tour_code}")
        return True
        
    except Exception as e:
        logger.error(f"Error in fill_charge_form: {e}")
        return False


def run_automation(start=0, limit=5, headless=False):
    """Main automation runner"""
    
    # Load data
    entries = load_csv_data(CONFIG['csv_path'], start, limit)
    logger.info(f"📊 Loaded {len(entries)} entries to process")
    
    results = []
    program_cache = {}  # Cache program codes
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()
        page.set_default_timeout(30000)
        
        # Login
        login(page)
        
        for i, entry in enumerate(entries):
            tour_code = entry['tour_code']
            amount = entry['amount']
            
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing [{i+1}/{len(entries)}]: {tour_code}")
            logger.info(f"{'='*60}")
            
            try:
                # Get program code (with caching by prefix)
                prefix_match = re.match(r'^([A-Z0-9]+?)(\d+N)', tour_code)
                prefix = prefix_match.group(1) if prefix_match else tour_code[:5]
                
                if prefix in program_cache:
                    program_code = program_cache[prefix]
                    logger.info(f"📦 Using cached program code: {program_code}")
                else:
                    program_code = find_program_code(page, tour_code)
                    if program_code:
                        program_cache[prefix] = program_code
                
                if not program_code:
                    results.append({
                        'tour_code': tour_code,
                        'status': 'FAILED',
                        'reason': 'Program code not found'
                    })
                    continue
                
                # Fill form
                success = fill_charge_form(page, tour_code, program_code, amount)
                
                results.append({
                    'tour_code': tour_code,
                    'program_code': program_code,
                    'amount': amount,
                    'status': 'SUCCESS' if success else 'FAILED',
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"❌ Error processing {tour_code}: {e}")
                results.append({
                    'tour_code': tour_code,
                    'status': 'FAILED',
                    'reason': str(e)
                })
            
            time.sleep(1)  # Delay between entries
        
        browser.close()
    
    # Save results
    output_file = f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
        if results:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
    
    # Print summary
    success_count = sum(1 for r in results if r.get('status') == 'SUCCESS')
    logger.info(f"\n{'='*60}")
    logger.info(f"📊 SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Total: {len(results)}")
    logger.info(f"✅ Success: {success_count}")
    logger.info(f"❌ Failed: {len(results) - success_count}")
    logger.info(f"📁 Results saved to: {output_file}")
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Tour Charge Automation')
    parser.add_argument('--start', type=int, default=0, help='Start row (0-indexed)')
    parser.add_argument('--limit', type=int, default=5, help='Max entries to process')
    parser.add_argument('--headless', action='store_true', help='Run browser in headless mode')
    parser.add_argument('--all', action='store_true', help='Process all entries')
    
    args = parser.parse_args()
    
    limit = None if args.all else args.limit
    run_automation(start=args.start, limit=limit, headless=args.headless)
