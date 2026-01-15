"""
Simple Tour Charge Automation - Uses same approach as manual browser testing
"""

import csv
import time
import re
import logging
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright

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
    page.goto(CONFIG['login_url'], wait_until='domcontentloaded')
    time.sleep(2)
    
    # Fill login form
    page.fill('input[type="text"]', CONFIG['username'])
    page.fill('input[type="password"]', CONFIG['password'])
    page.click('button:has-text("Login")')
    time.sleep(3)
    logger.info("✅ Logged in successfully")


def find_program_code(page, tour_code):
    """Find program code by searching in tour program list"""
    logger.info(f"🔍 Searching for program code: {tour_code}")
    
    page.goto(CONFIG['tour_program_url'], wait_until='domcontentloaded')
    time.sleep(2)
    
    # Find the keyword search box
    page.fill('input[placeholder*="keyword"], input[placeholder*="ชื่อโปรแกรม"]', tour_code)
    page.click('button:has-text("Go!")')
    time.sleep(3)
    
    # Extract program code from page content
    content = page.content()
    
    # Get prefix from tour code (e.g., 2UCKG from 2UCKG4NCKGFD251206)
    prefix_match = re.match(r'^([A-Z0-9]+?)(\d+N)', tour_code)
    prefix = prefix_match.group(1) if prefix_match else tour_code[:5]
    
    # Find program code pattern
    pattern = rf'{prefix}-[A-Z]{{2}}\d{{3}}'
    matches = re.findall(pattern, content)
    
    if matches:
        logger.info(f"✅ Found program code: {matches[0]}")
        return matches[0]
    
    logger.warning(f"⚠️ Program code not found for {tour_code}")
    return None


def fill_form_via_url(page, tour_code, program_code, amount):
    """
    Fill the charge form by navigating directly and using precise selectors.
    """
    logger.info(f"📝 Filling form: {tour_code} | {program_code} | {amount}")
    
    page.goto(CONFIG['charges_url'], wait_until='domcontentloaded')
    time.sleep(3)
    
    # Change date range by clicking and navigating datepicker
    # Start date input
    start_input = page.locator('input.form-control').first
    start_input.click()
    time.sleep(0.5)
    
    # Go back many months to cover all tours
    for _ in range(24):
        prev = page.locator('.datepicker .prev, .prev').first
        if prev.is_visible():
            prev.click()
            time.sleep(0.05)
    
    # Select first day
    page.locator('.datepicker td.day').first.click()
    time.sleep(0.3)
    page.keyboard.press('Escape')
    time.sleep(0.5)
    
    # Now select program
    program_dropdown = page.locator('button.dropdown-toggle').first
    program_dropdown.click()
    time.sleep(0.5)
    
    # Type in search
    page.locator('.bs-searchbox input').first.fill(program_code)
    time.sleep(0.5)
    
    # Click option
    page.locator(f'li a:has-text("{program_code}")').first.click()
    time.sleep(1)
    
    # Select tour code
    tour_dropdown = page.locator('button.dropdown-toggle').nth(1)
    tour_dropdown.click()
    time.sleep(0.5)
    
    page.locator(f'li a:has-text("{tour_code}")').first.click()
    time.sleep(0.5)
    
    # Fill other fields
    payment_date = get_payment_date()
    
    # Use JavaScript for the remaining fields - with correct field names
    page.evaluate(f'''() => {{
        // Payment date
        const paymentDateInput = document.querySelector('input[name="payment_date"]');
        if (paymentDateInput) paymentDateInput.value = '{payment_date}';
        
        // Description
        const descInput = document.querySelector('input[name="description[]"]');
        if (descInput) descInput.value = '{CONFIG["description"]}';
        
        // Type (rate_type)
        const typeSelect = document.querySelector('select[name="rate_type[]"]');
        if (typeSelect) {{
            for (let opt of typeSelect.options) {{
                if (opt.text === '{CONFIG["charge_type"]}') {{
                    typeSelect.value = opt.value;
                    break;
                }}
            }}
        }}
        
        // Amount (price)
        const amountInput = document.querySelector('input[name="price[]"]');
        if (amountInput) amountInput.value = '{amount}';
    }}''')
    time.sleep(0.5)
    
    # Save
    page.click('button:has-text("Save")')
    time.sleep(3)
    
    logger.info(f"✅ Form submitted for {tour_code}")
    return True


def run_automation(start=0, limit=3, headless=False):
    """Main automation runner"""
    
    entries = load_csv_data(CONFIG['csv_path'], start, limit)
    logger.info(f"📊 Loaded {len(entries)} entries to process")
    
    results = []
    program_cache = {}
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, slow_mo=100)
        page = browser.new_page()
        page.set_default_timeout(60000)  # 60 second timeout
        
        login(page)
        
        for i, entry in enumerate(entries):
            tour_code = entry['tour_code']
            amount = entry['amount']
            
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing [{i+1}/{len(entries)}]: {tour_code}")
            logger.info(f"{'='*60}")
            
            try:
                # Get program code (with caching)
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
                success = fill_form_via_url(page, tour_code, program_code, amount)
                
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
                    'reason': str(e)[:100]
                })
            
            time.sleep(1)
        
        browser.close()
    
    # Save results
    output_file = f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
        if results:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
    
    # Summary
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
    parser.add_argument('--start', type=int, default=0, help='Start row')
    parser.add_argument('--limit', type=int, default=3, help='Max entries')
    parser.add_argument('--headless', action='store_true', help='Run headless')
    parser.add_argument('--all', action='store_true', help='Process all')
    
    args = parser.parse_args()
    
    limit = None if args.all else args.limit
    run_automation(start=args.start, limit=limit, headless=args.headless)
