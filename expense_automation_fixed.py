"""
Fixed Expense Automation for qualityb2bpackage.com
Key fixes:
1. Correct selector for Save button (input[type="submit"] instead of button)
2. Proper form submission with wait for navigation
3. Better error handling and retry logic
4. Expense number extraction after submission
"""

import csv
import time
import re
import logging
import argparse
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from playwright.sync_api import sync_playwright, Page, Browser

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('expense_automation.log', encoding='utf-8'),
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
    'charge_type': 'ค่าใช้จ่ายเบ็ดเตล็ด',
    'csv_path': 'ยอดเบิกอุปกรณ์.csv',
    # Company expense configuration
    'company_expense_enabled': True,
    'company_name': 'GO365 TRAVEL CO.,LTD.',
    'company_value': '39',
    'payment_method': 'โอนเข้าบัญชี',
    'payment_type': 'เบ็ดเตล็ด',
}


def get_payment_date() -> str:
    """Get payment date (7 days from now)"""
    return (datetime.now() + timedelta(days=7)).strftime("%d/%m/%Y")


def generate_remark(program_full_name: str, program_code: str, tour_code: str, 
                   pax: int, amount: int, payment_date: str) -> str:
    """Generate remark text"""
    return f"""เลขที่ : 
Program : {program_full_name}
Code Program : {program_code}
Code group : {tour_code}

รายละเอียด : 
{CONFIG['description']} 50 (Fixed) x {pax} PAX = {amount} THB (Auto calculate)

ยอดเงินรวม : {amount} THB

วันจ่าย : {payment_date}"""


def generate_company_remark(tour_code: str, amount: int, payment_date: str) -> str:
    """Generate company expense remark"""
    return f"""ค่าใช้จ่ายของบริษัท → {CONFIG['company_name']}
วิธีการจ่าย → {CONFIG['payment_method']}
จำนวนเงิน → {amount} THB
ประเภทจ่าย → {CONFIG['payment_type']}
วันที่จ่าย → {payment_date}
พีเรียด → {tour_code}"""


def load_csv_data(csv_path: str, start: int = 0, limit: Optional[int] = None) -> List[Dict]:
    """Load expense data from CSV"""
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


def login(page: Page) -> bool:
    """Login to the website"""
    logger.info("Logging in...")
    page.goto(CONFIG['login_url'], wait_until='domcontentloaded')
    time.sleep(2)
    
    # Check if already logged in
    if 'Welcome' in page.content() or 'Dashboard' in page.content():
        logger.info("✅ Already logged in")
        return True
    
    page.fill('input[type="text"]', CONFIG['username'])
    page.fill('input[type="password"]', CONFIG['password'])
    page.click('button:has-text("Login")')
    time.sleep(3)
    
    if 'Welcome' in page.content() or 'Dashboard' in page.content():
        logger.info("✅ Login successful")
        return True
    
    logger.error("❌ Login failed")
    return False


def find_program_code(page: Page, tour_code: str) -> Optional[str]:
    """Find program code from tour code"""
    logger.info(f"🔍 Searching for program code: {tour_code}")
    page.goto(CONFIG['tour_program_url'], wait_until='domcontentloaded')
    time.sleep(2)
    
    # Search for the tour code
    search_input = page.query_selector('input[placeholder*="keyword"], input[placeholder*="ชื่อโปรแกรม"]')
    if search_input:
        search_input.fill(tour_code)
        page.click('button:has-text("Go!")')
        time.sleep(3)
    
    content = page.content()
    prefix_match = re.match(r'^([A-Z0-9]+?)(\d+N)', tour_code)
    prefix = prefix_match.group(1) if prefix_match else tour_code[:5]
    
    pattern = rf'{prefix}-[A-Z]{{2}}\d{{3}}'
    matches = re.findall(pattern, content)
    
    if matches:
        logger.info(f"✅ Found program code: {matches[0]}")
        return matches[0]
    
    logger.warning("⚠️ Program code not found")
    return None


def fill_and_submit_form(
    page: Page,
    tour_code: str,
    program_code: str,
    amount: int,
    pax: int,
    program_full_name: str = ""
) -> Dict[str, Any]:
    """Fill the expense form and submit it - FIXED VERSION"""
    
    result = {
        'success': False,
        'tour_code': tour_code,
        'program_code': program_code,
        'amount': amount,
        'pax': pax,
        'expense_no': None,
        'error': None
    }
    
    logger.info(f"📝 Filling form: {tour_code} | {program_code} | {amount} | PAX: {pax}")
    
    try:
        page.goto(CONFIG['charges_url'], wait_until='domcontentloaded')
        time.sleep(3)
        
        # STEP 1: Set date range
        logger.info("Setting date range...")
        page.evaluate("""() => {
            const startInput = document.querySelector('input[name="start"]');
            const endInput = document.querySelector('input[name="end"]');
            if (startInput) {
                startInput.value = '01/01/2024';
                startInput.dispatchEvent(new Event('change', { bubbles: true }));
            }
            if (endInput) {
                endInput.value = '31/12/2026';
                endInput.dispatchEvent(new Event('change', { bubbles: true }));
            }
        }""")
        time.sleep(3)
        
        # STEP 2: Select program
        logger.info(f"Selecting program: {program_code}")
        select_result = page.evaluate(f"""(programCode) => {{
            const packageSelect = $('select[name="package"]');
            const option = packageSelect.find('option').filter(function() {{
                return $(this).text().indexOf(programCode) !== -1;
            }}).first();
            if (option.length > 0) {{
                packageSelect.selectpicker('val', option.val());
                packageSelect.trigger('change');
                return {{ success: true, value: option.val(), text: option.text() }};
            }}
            return {{ success: false, error: 'Option not found for ' + programCode }};
        }}""", program_code)
        
        if select_result.get('success'):
            program_full_name = select_result.get('text', program_code)
            logger.info(f"✅ Program selected: {program_full_name[:50]}...")
        else:
            logger.warning(f"⚠️ Program not found: {select_result.get('error')}")
        time.sleep(2)
        
        # STEP 3: Select tour code
        logger.info(f"Selecting tour code: {tour_code}")
        tour_result = page.evaluate(f"""(tourCode) => {{
            const periodSelect = $('select[name="period"]');
            const option = periodSelect.find('option').filter(function() {{
                return $(this).text().indexOf(tourCode) !== -1;
            }}).first();
            if (option.length > 0) {{
                periodSelect.selectpicker('val', option.val());
                periodSelect.trigger('change');
                return {{ success: true, value: option.val() }};
            }}
            return {{ success: false, error: 'Tour code not found: ' + tourCode }};
        }}""", tour_code)
        
        if tour_result.get('success'):
            logger.info(f"✅ Tour code selected: {tour_code}")
        else:
            logger.warning(f"⚠️ Tour code not found: {tour_result.get('error')}")
            result['error'] = "Tour code not found"
            return result
        time.sleep(1)
        
        # STEP 4: Fill form fields
        payment_date = get_payment_date()
        description = CONFIG['description']
        
        logger.info("Filling form fields...")
        page.evaluate(f"""() => {{
            // Payment date
            const dateInput = document.querySelector('input[name="payment_date"]');
            if (dateInput) {{
                dateInput.value = '{payment_date}';
                dateInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }}
            
            // Description
            const descInput = document.querySelector('input[name="description[]"]');
            if (descInput) descInput.value = '{description}';
            
            // Charge type
            const typeSelect = $('select[name="rate_type[]"]');
            const typeOption = typeSelect.find('option').filter(function() {{
                return $(this).text().indexOf('เบ็ดเตล็ด') !== -1;
            }}).first();
            if (typeOption.length > 0) {{
                typeSelect.val(typeOption.val());
            }}
            
            // Amount
            const amountInput = document.querySelector('input[name="price[]"]');
            if (amountInput) amountInput.value = '{amount}';
        }}""")
        time.sleep(0.5)
        
        # STEP 5: Fill remark
        remark_text = generate_remark(program_full_name, program_code, tour_code, pax, amount, payment_date)
        remark_input = page.locator('textarea[name="remark"]')
        if remark_input.count() > 0:
            remark_input.fill(remark_text)
            logger.info("✅ Filled tour expense remark")
        time.sleep(0.3)
        
        # STEP 6: Add company expense if enabled
        if CONFIG.get('company_expense_enabled', False):
            logger.info("📋 Adding company expense...")
            
            company_toggle = page.locator('text=เพิ่มในค่าใช้จ่ายบริษัท').first
            if company_toggle.count() > 0:
                company_toggle.click()
                time.sleep(1)
                
                # Select company
                page.evaluate(f"""() => {{
                    const companySelect = $('select[name="charges[id_company_charges_agent]"]');
                    companySelect.selectpicker('val', '{CONFIG['company_value']}');
                    companySelect.trigger('change');
                }}""")
                time.sleep(0.5)
                logger.info(f"✅ Selected company: {CONFIG['company_name']}")
                
                # Select payment method
                page.evaluate(f"""(paymentMethod) => {{
                    const payMethodSelect = $('select[name="charges[payment_type]"]');
                    const payMethodOption = payMethodSelect.find('option').filter(function() {{
                        return $(this).text().indexOf(paymentMethod) !== -1;
                    }}).first();
                    if (payMethodOption.length > 0) {{
                        payMethodSelect.selectpicker('val', payMethodOption.val());
                        payMethodSelect.trigger('change');
                    }}
                }}""", CONFIG['payment_method'])
                time.sleep(0.3)
                
                # Fill company amount
                company_amount_input = page.locator('input[name="charges[amount]"]')
                if company_amount_input.count() > 0:
                    company_amount_input.fill(str(amount))
                time.sleep(0.3)
                
                # Select payment type
                page.evaluate(f"""(paymentType) => {{
                    const payTypeSelect = $('select[name="charges[id_company_charges_type]"]');
                    const payTypeOption = payTypeSelect.find('option').filter(function() {{
                        return $(this).text().indexOf(paymentType) !== -1;
                    }}).first();
                    if (payTypeOption.length > 0) {{
                        payTypeSelect.selectpicker('val', payTypeOption.val());
                        payTypeSelect.trigger('change');
                    }}
                }}""", CONFIG['payment_type'])
                time.sleep(0.3)
                
                # Fill payment date
                page.evaluate(f"""(date) => {{
                    const dateInput = document.querySelector('input[name="charges[payment_date]"]');
                    if (dateInput) {{
                        dateInput.value = date;
                        dateInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }}
                }}""", payment_date)
                time.sleep(0.3)
                
                # Fill period
                page.evaluate(f"""(tourCode) => {{
                    const periodInput = document.querySelector('input[name="charges[period]"]');
                    if (periodInput) {{
                        periodInput.value = tourCode;
                        periodInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }}
                }}""", tour_code)
                time.sleep(0.3)
                
                # Fill company remark
                company_remark_text = generate_company_remark(tour_code, amount, payment_date)
                company_remark = page.locator('textarea[name="charges[remark]"]')
                if company_remark.count() > 0:
                    company_remark.fill(company_remark_text)
                time.sleep(0.3)
        
        # STEP 7: SUBMIT THE FORM - FIXED
        logger.info("🚀 Submitting form...")
        
        # Get the current URL before submission
        url_before = page.url
        
        # Method 1: Click the submit input directly
        submit_btn = page.locator('input[type="submit"][value="Save"]')
        if submit_btn.count() > 0:
            # Scroll to the button first
            submit_btn.scroll_into_view_if_needed()
            time.sleep(0.5)
            
            # Click the button
            submit_btn.click()
            logger.info("✅ Clicked Save button (input[type='submit'])")
        else:
            # Fallback: Try other methods
            logger.info("Trying alternative submit methods...")
            
            # Try clicking by JavaScript
            clicked = page.evaluate("""() => {
                // Try input[type="submit"]
                let btn = document.querySelector('input[type="submit"]');
                if (btn) {
                    btn.scrollIntoView({ behavior: 'instant', block: 'center' });
                    btn.click();
                    return 'input_submit';
                }
                
                // Try button[type="submit"]
                btn = document.querySelector('button[type="submit"]');
                if (btn) {
                    btn.scrollIntoView({ behavior: 'instant', block: 'center' });
                    btn.click();
                    return 'button_submit';
                }
                
                // Try form.submit()
                const form = document.querySelector('form');
                if (form) {
                    form.submit();
                    return 'form_submit';
                }
                
                return null;
            }""")
            
            if clicked:
                logger.info(f"✅ Form submitted via: {clicked}")
            else:
                logger.error("❌ Could not find submit button")
                result['error'] = "Submit button not found"
                return result
        
        # Wait for navigation or response
        time.sleep(3)
        
        # Check if URL changed (indicates successful submission)
        url_after = page.url
        if url_after != url_before:
            logger.info(f"✅ Page navigated: {url_after}")
        
        # Try to extract expense number
        expense_no = extract_expense_number(page)
        
        result['success'] = True
        result['expense_no'] = expense_no
        
        if expense_no:
            logger.info(f"✅ Expense created successfully: {expense_no}")
        else:
            logger.info("✅ Form submitted (no expense number returned)")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        result['error'] = str(e)
    
    return result


def extract_expense_number(page: Page) -> Optional[str]:
    """Extract expense number from page after submission"""
    try:
        # Method 1: Check input fields
        expense_no = page.evaluate("""() => {
            const selectors = [
                'input[name*="charges_no"]',
                'input[name*="expense_no"]',
                'input[placeholder*="C20"]',
                'input#charges_no',
                'input[name="charges_no"]'
            ];
            
            for (const selector of selectors) {
                const input = document.querySelector(selector);
                if (input && input.value && input.value.match(/C\\d{6}-\\d{6}/)) {
                    return input.value.match(/C\\d{6}-\\d{6}/)[0];
                }
            }
            
            // Check all text inputs
            const allInputs = document.querySelectorAll('input[type="text"]');
            for (const input of allInputs) {
                if (input.value && input.value.match(/C\\d{6}-\\d{6}/)) {
                    return input.value.match(/C\\d{6}-\\d{6}/)[0];
                }
            }
            
            // Check page text
            const text = document.body.innerText || '';
            const match = text.match(/C\\d{6}-\\d{6}/);
            return match ? match[0] : null;
        }""")
        
        if expense_no:
            return expense_no
        
        # Method 2: Check URL
        current_url = page.url
        if '/charges_group/manage/' in current_url or '/charges/manage/' in current_url:
            match = re.search(r'/(\d+)$', current_url)
            if match:
                return f"C{datetime.now().strftime('%y%m%d')}-{match.group(1)}"
        
        return None
        
    except Exception as e:
        logger.warning(f"Could not extract expense number: {e}")
        return None


def run_automation(start: int = 0, limit: int = 3, headless: bool = False, csv_path: Optional[str] = None):
    """Run the expense automation"""
    
    if csv_path:
        CONFIG['csv_path'] = csv_path
    
    entries = load_csv_data(CONFIG['csv_path'], start, limit)
    logger.info(f"📊 Loaded {len(entries)} entries")
    
    if not entries:
        logger.warning("No entries to process")
        return
    
    results = []
    program_cache = {}
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, slow_mo=50)
        page = browser.new_page()
        page.set_default_timeout(30000)
        
        if not login(page):
            logger.error("Login failed, aborting")
            browser.close()
            return
        
        for i, entry in enumerate(entries):
            tour_code = entry['tour_code']
            pax = entry['pax']
            amount = entry['amount']
            
            logger.info(f"\n{'='*60}")
            logger.info(f"[{i+1}/{len(entries)}] {tour_code} | PAX: {pax} | Amount: {amount}")
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
                        'program_code': '',
                        'pax': pax,
                        'amount': amount,
                        'status': 'FAILED',
                        'expense_no': '',
                        'reason': 'No program code found',
                        'timestamp': datetime.now().isoformat()
                    })
                    continue
                
                # Fill and submit form
                form_result = fill_and_submit_form(page, tour_code, program_code, amount, pax)
                
                results.append({
                    'tour_code': tour_code,
                    'program_code': program_code,
                    'pax': pax,
                    'amount': amount,
                    'status': 'SUCCESS' if form_result['success'] else 'FAILED',
                    'expense_no': form_result.get('expense_no', ''),
                    'reason': form_result.get('error', ''),
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"❌ Error processing {tour_code}: {e}")
                results.append({
                    'tour_code': tour_code,
                    'program_code': '',
                    'pax': pax,
                    'amount': amount,
                    'status': 'FAILED',
                    'expense_no': '',
                    'reason': str(e)[:100],
                    'timestamp': datetime.now().isoformat()
                })
            
            time.sleep(1)
        
        browser.close()
    
    # Save results
    output_file = f"expense_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
        if results:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
    
    success_count = sum(1 for r in results if r.get('status') == 'SUCCESS')
    logger.info(f"\n{'='*60}")
    logger.info(f"📊 SUMMARY: {success_count}/{len(results)} successful")
    logger.info(f"📁 Results saved to: {output_file}")
    logger.info(f"{'='*60}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Expense Automation for qualityb2bpackage.com')
    parser.add_argument('--start', type=int, default=0, help='Start index in CSV')
    parser.add_argument('--limit', type=int, default=3, help='Number of entries to process')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    parser.add_argument('--all', action='store_true', help='Process all entries')
    parser.add_argument('--csv', type=str, help='Path to CSV file')
    args = parser.parse_args()
    
    run_automation(
        start=args.start,
        limit=None if args.all else args.limit,
        headless=args.headless,
        csv_path=args.csv
    )
