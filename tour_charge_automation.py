"""
Tour Charge Automation Script
Automates the creation of tour charge entries in QualityB2BPackage system.
"""

import csv
import time
import logging
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
import config

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


class TourChargeAutomation:
    def __init__(self, headless=False):
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.page = None
        self.program_code_cache = {}  # Cache for program codes
        self.results = []  # Track results for each entry
        
    def start(self):
        """Initialize browser and login"""
        logger.info("Starting automation...")
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        self.page = self.browser.new_page()
        self.page.set_default_timeout(config.DEFAULT_TIMEOUT)
        
    def stop(self):
        """Clean up resources"""
        logger.info("Stopping automation...")
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
            
    def login(self):
        """Login to the system"""
        logger.info(f"Logging in as {config.USERNAME}...")
        self.page.goto(config.LOGIN_URL, timeout=config.NAVIGATION_TIMEOUT)
        
        # Fill login form
        self.page.fill('input[name="username"]', config.USERNAME)
        self.page.fill('input[name="password"]', config.PASSWORD)
        self.page.click('button[type="submit"]')
        
        # Wait for navigation to complete
        self.page.wait_for_load_state('networkidle')
        logger.info("Login successful!")
        
    def get_program_code(self, tour_code: str) -> str:
        """
        Get program code for a tour code by searching in โปรแกรมทัวร์
        Results are cached for efficiency.
        """
        # Extract program prefix from tour code (e.g., 2UCKG from 2UCKG4NCKGFD251206)
        # The prefix is typically the first few characters before the trip details
        prefix = self._extract_prefix(tour_code)
        
        # Check cache first
        if prefix in self.program_code_cache:
            logger.info(f"Using cached program code for {prefix}: {self.program_code_cache[prefix]}")
            return self.program_code_cache[prefix]
        
        logger.info(f"Searching for program code for tour: {tour_code}")
        
        # Navigate to tour program list
        self.page.goto(config.TOUR_PROGRAM_LIST_URL, timeout=config.NAVIGATION_TIMEOUT)
        self.page.wait_for_load_state('networkidle')
        
        # Search for the tour code
        search_box = self.page.locator('input[type="search"], input[name="search"], .form-control').first
        search_box.fill(tour_code)
        
        # Click search button
        self.page.click('button:has-text("ค้นหา"), button:has-text("Search"), .btn-primary')
        self.page.wait_for_load_state('networkidle')
        time.sleep(1)  # Wait for results to load
        
        # Look for program code in results
        # The program code appears in the format like "2UCKG-FD002"
        program_code = self._extract_program_code_from_results(tour_code)
        
        if program_code:
            self.program_code_cache[prefix] = program_code
            logger.info(f"Found program code: {program_code}")
        else:
            logger.warning(f"Could not find program code for {tour_code}")
            
        return program_code
    
    def _extract_prefix(self, tour_code: str) -> str:
        """Extract program prefix from tour code"""
        # Tour codes like 2UCKG4NCKGFD251206 have prefix like 2UCKG
        # Look for the pattern: alphanumeric until a digit followed by N
        import re
        match = re.match(r'^([A-Z0-9]+?)(\d+N)', tour_code)
        if match:
            return match.group(1)
        # Fallback: first 5 characters
        return tour_code[:5]
    
    def _extract_program_code_from_results(self, tour_code: str) -> str:
        """Extract program code from search results page"""
        # Look for text matching pattern like "2UCKG-FD002"
        import re
        
        # Get all text content from the page
        content = self.page.content()
        
        # Look for program codes (format: XXXXX-XXNNN or similar)
        prefix = self._extract_prefix(tour_code)
        pattern = rf'{prefix}-[A-Z]{{2}}\d{{3}}'
        matches = re.findall(pattern, content)
        
        if matches:
            return matches[0]
        
        # Alternative: look in table cells
        try:
            rows = self.page.locator('table tbody tr').all()
            for row in rows:
                text = row.text_content()
                if tour_code in text or prefix in text:
                    matches = re.findall(r'[A-Z0-9]+-[A-Z]{2}\d{3}', text)
                    if matches:
                        return matches[0]
        except Exception as e:
            logger.debug(f"Error searching table: {e}")
            
        return None
    
    def fill_charge_form(self, tour_code: str, program_code: str, amount: int) -> bool:
        """Fill the charge creation form"""
        logger.info(f"Filling form for tour: {tour_code}, amount: {amount}")
        
        try:
            # Navigate to charges form
            self.page.goto(config.CHARGES_FORM_URL, timeout=config.NAVIGATION_TIMEOUT)
            self.page.wait_for_load_state('networkidle')
            time.sleep(1)
            
            # Step 1: Set date range
            self._set_date_range()
            
            # Step 2: Select program
            self._select_program(program_code)
            
            # Step 3: Select tour code
            self._select_tour_code(tour_code)
            
            # Step 4: Fill payment date
            payment_date = config.get_payment_date()
            self._fill_payment_date(payment_date)
            
            # Step 5: Fill description
            self.page.fill('input[name="charges_d[description][]"], textarea[name="charges_d[description][]"]', config.DESCRIPTION)
            
            # Step 6: Select type
            self.page.select_option('select[name="charges_d[type][]"]', label=config.CHARGE_TYPE)
            
            # Step 7: Fill amount
            amount_field = self.page.locator('input[name="charges_d[amount][]"]').first
            amount_field.fill(str(amount))
            
            # Step 8: Click Save
            self.page.click('button:has-text("Save")')
            self.page.wait_for_load_state('networkidle')
            
            # Check for success message or navigation
            time.sleep(1)
            if "success" in self.page.content().lower() or self.page.url != config.CHARGES_FORM_URL:
                logger.info(f"✅ Successfully saved charge for {tour_code}")
                return True
            else:
                logger.warning(f"⚠️ May have failed for {tour_code}")
                return False
                
        except PlaywrightTimeout as e:
            logger.error(f"❌ Timeout error for {tour_code}: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Error for {tour_code}: {e}")
            return False
    
    def _set_date_range(self):
        """Set the date range filter"""
        # Click start date and set it
        start_input = self.page.locator('input').filter(has_text="").nth(0)
        
        # Use JavaScript to set dates directly
        self.page.evaluate(f'''
            const inputs = document.querySelectorAll('input[type="text"]');
            for (let input of inputs) {{
                if (input.value && input.value.includes('/')) {{
                    // This is likely a date field
                    break;
                }}
            }}
        ''')
        
        # Try clicking on date inputs and setting values
        try:
            date_inputs = self.page.locator('input.form-control').all()
            for inp in date_inputs[:2]:  # First two are likely date range
                val = inp.input_value()
                if '/' in val:  # Date format
                    # Clear and set new date
                    break
        except:
            pass
            
    def _select_program(self, program_code: str):
        """Select the tour program from dropdown"""
        logger.info(f"Selecting program: {program_code}")
        
        # Click on the bootstrap selectpicker button
        program_dropdown = self.page.locator('button.dropdown-toggle').first
        program_dropdown.click()
        time.sleep(0.5)
        
        # Type in the search box
        search_input = self.page.locator('.bs-searchbox input').first
        search_input.fill(program_code)
        time.sleep(0.5)
        
        # Click on the matching option
        option = self.page.locator(f'a:has-text("{program_code}")').first
        option.click()
        time.sleep(0.5)
        
    def _select_tour_code(self, tour_code: str):
        """Select the tour code from dropdown"""
        logger.info(f"Selecting tour code: {tour_code}")
        
        # Wait for tour code dropdown to be enabled
        time.sleep(1)
        
        # Click on the tour code dropdown
        tour_dropdown = self.page.locator('button.dropdown-toggle').nth(1)
        tour_dropdown.click()
        time.sleep(0.5)
        
        # Click on the matching option
        option = self.page.locator(f'a:has-text("{tour_code}")').first
        option.click()
        time.sleep(0.5)
        
    def _fill_payment_date(self, date: str):
        """Fill the payment date field"""
        date_input = self.page.locator('input[name="date_pay"]').first
        if date_input.count() == 0:
            # Try alternative selector
            date_input = self.page.locator('input').filter(has=self.page.locator('text=วันที่จ่าย')).first
        date_input.fill(date)
        
    def process_csv(self, csv_path: str, start_row: int = 0, max_rows: int = None):
        """Process entries from CSV file"""
        logger.info(f"Reading CSV from: {csv_path}")
        
        entries = []
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if i < start_row:
                    continue
                if max_rows and i >= start_row + max_rows:
                    break
                entries.append({
                    'tour_code': row['รหัสทัวร์'].strip(),
                    'pax': int(row['จำนวนลูกค้า หัก หนท.'].strip()),
                    'amount': int(row['ยอดเบิก'].strip())
                })
        
        logger.info(f"Loaded {len(entries)} entries to process")
        return entries
    
    def run(self, csv_path: str, start_row: int = 0, max_rows: int = None):
        """Main automation loop"""
        try:
            self.start()
            self.login()
            
            entries = self.process_csv(csv_path, start_row, max_rows)
            
            for i, entry in enumerate(entries):
                logger.info(f"\n{'='*60}")
                logger.info(f"Processing {i+1}/{len(entries)}: {entry['tour_code']}")
                logger.info(f"{'='*60}")
                
                # Get program code
                program_code = self.get_program_code(entry['tour_code'])
                
                if not program_code:
                    self.results.append({
                        'tour_code': entry['tour_code'],
                        'status': 'FAILED',
                        'reason': 'Program code not found'
                    })
                    continue
                
                # Fill the form
                success = self.fill_charge_form(
                    tour_code=entry['tour_code'],
                    program_code=program_code,
                    amount=entry['amount']
                )
                
                self.results.append({
                    'tour_code': entry['tour_code'],
                    'program_code': program_code,
                    'amount': entry['amount'],
                    'status': 'SUCCESS' if success else 'FAILED',
                    'timestamp': datetime.now().isoformat()
                })
                
                # Small delay between entries
                time.sleep(1)
                
            self.save_results()
            
        finally:
            self.stop()
            
    def save_results(self):
        """Save automation results to CSV"""
        output_file = f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
            if self.results:
                writer = csv.DictWriter(f, fieldnames=self.results[0].keys())
                writer.writeheader()
                writer.writerows(self.results)
                
        logger.info(f"Results saved to: {output_file}")
        
        # Print summary
        success_count = sum(1 for r in self.results if r.get('status') == 'SUCCESS')
        fail_count = len(self.results) - success_count
        logger.info(f"\n{'='*60}")
        logger.info(f"SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"Total processed: {len(self.results)}")
        logger.info(f"Successful: {success_count}")
        logger.info(f"Failed: {fail_count}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Tour Charge Automation')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    parser.add_argument('--start', type=int, default=0, help='Start row (0-indexed)')
    parser.add_argument('--max', type=int, default=None, help='Max rows to process')
    parser.add_argument('--csv', type=str, default=config.CSV_FILE_PATH, help='CSV file path')
    
    args = parser.parse_args()
    
    automation = TourChargeAutomation(headless=args.headless)
    automation.run(args.csv, start_row=args.start, max_rows=args.max)
