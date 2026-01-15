"""
Robust Tour Charge Automation - Using direct keyboard/mouse interactions
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

CONFIG = {
    'username': 'noi',
    'password': 'PrayuthChanocha112',
    'login_url': 'https://www.qualityb2bpackage.com/',
    'charges_url': 'https://www.qualityb2bpackage.com/charges_group/create',
    'tour_program_url': 'https://www.qualityb2bpackage.com/travelpackage',
    'description': 'ค่าอุปกรณ์ออกทัวร์',
    'charge_type': 'ค่าใช้จ่ายเบ็ดเตล็ด',  # ประเภท for tour expense - เบ็ดเตล็ด
    'csv_path': r'C:\Users\saksi\OneDrive\文档\order-bot\ยอดเบิกอุปกรณ์.csv',
    # Company expense configuration
    'company_expense_enabled': True,
    'company_name': 'GO365 TRAVEL CO.,LTD.',
    'company_value': '39',  # Value for GO365 TRAVEL CO.,LTD.
    'payment_method': 'โอนเข้าบัญชี',  # วิธีการจ่าย (Payment method) for company expense
    'payment_type': 'เบ็ดเตล็ด',  # ประเภทจ่าย (Payment type) for company expense
}


def get_payment_date():
    return (datetime.now() + timedelta(days=7)).strftime("%d/%m/%Y")


def remark_template(program_full_name, program_code, group_code, pax, amount, payment_date):
    """Generate remark text with all details"""
    template = f"""เลขที่ : 
Program : {program_full_name}
Code Program : {program_code}
Code group : {group_code}

รายละเอียด : 
{CONFIG['description']} 50 (Fixed) x {pax} PAX = {amount} THB (Auto calculate)

ยอดเงินรวม : {amount} THB

วันจ่าย : {payment_date}"""
    return template


def load_csv_data(csv_path, start=0, limit=None):
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
    logger.info("Logging in...")
    page.goto(CONFIG['login_url'], wait_until='domcontentloaded')
    time.sleep(2)
    page.fill('input[type="text"]', CONFIG['username'])
    page.fill('input[type="password"]', CONFIG['password'])
    page.click('button:has-text("Login")')
    time.sleep(3)
    logger.info("✅ Logged in successfully")


def find_program_code(page, tour_code):
    logger.info(f"🔍 Searching for program code: {tour_code}")
    page.goto(CONFIG['tour_program_url'], wait_until='domcontentloaded')
    time.sleep(2)
    
    page.fill('input[placeholder*="keyword"], input[placeholder*="ชื่อโปรแกรม"]', tour_code)
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
    
    logger.warning(f"⚠️ Program code not found")
    return None


def fill_form(page, tour_code, program_code, amount, pax, program_full_name=""):
    """Fill the charge form using JavaScript injection for Bootstrap selectpicker"""
    logger.info(f"📝 Filling form: {tour_code} | {program_code} | {amount} | PAX: {pax}")
    
    page.goto(CONFIG['charges_url'], wait_until='domcontentloaded')
    time.sleep(3)
    
    # STEP 1: Update date range using JavaScript
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
    time.sleep(3)  # Wait for AJAX reload
    
    # STEP 2: Select program using jQuery selectpicker
    logger.info(f"Selecting program: {program_code}")
    result = page.evaluate(f"""(programCode) => {{
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
    
    if result.get('success'):
        program_full_name = result.get('text', program_code)
        logger.info(f"✅ Program selected: {program_full_name}")
    else:
        logger.warning(f"⚠️ Program not found: {result.get('error')}")
    time.sleep(2)
    
    # STEP 3: Select tour code using jQuery selectpicker
    logger.info(f"Selecting tour code: {tour_code}")
    result = page.evaluate(f"""(tourCode) => {{
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
    
    if result.get('success'):
        logger.info(f"✅ Tour code selected: {tour_code}")
    else:
        logger.warning(f"⚠️ Tour code not found: {result.get('error')}")
        return False
    time.sleep(1)
    
    # STEP 4: Fill remaining fields using JavaScript
    payment_date = get_payment_date()
    description = CONFIG['description']
    charge_type = CONFIG['charge_type']
    
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
        
        // Charge type using selectpicker (ประเภท - เบ็ดเตล็ด)
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
    
    # STEP 6: Fill remark for tour expense
    payment_date = get_payment_date()
    remark_text = remark_template(
        program_full_name=program_full_name,
        program_code=program_code,
        group_code=tour_code,
        pax=pax,
        amount=amount,
        payment_date=payment_date
    )
    
    remark_input = page.locator('textarea[name="remark"]')
    if remark_input.count() > 0:
        remark_input.fill(remark_text)
        logger.info("✅ Filled tour expense remark")
    time.sleep(0.3)
    
    # STEP 7: Add company expense if enabled
    if CONFIG.get('company_expense_enabled', False):
        logger.info("📋 Adding company expense...")
        
        # Click the checkbox/toggle to show company expense section
        # The element has "เพิ่มในค่าใช้จ่ายบริษัท" text
        company_toggle = page.locator('text=เพิ่มในค่าใช้จ่ายบริษัท').first
        if company_toggle.count() > 0:
            company_toggle.click()
            time.sleep(1)
            
            # Select company using JavaScript (Bootstrap selectpicker)
            page.evaluate(f"""() => {{
                const companySelect = $('select[name="charges[id_company_charges_agent]"]');
                companySelect.selectpicker('val', '{CONFIG['company_value']}');
                companySelect.trigger('change');
            }}""")
            time.sleep(0.5)
            logger.info(f"✅ Selected company: {CONFIG['company_name']}")
            
            # Select payment method (วิธีการจ่าย) - "โอนเข้าบัญชี"
            payment_method = CONFIG.get('payment_method', 'โอนเข้าบัญชี')
            page.evaluate(f"""(paymentMethod) => {{
                const payMethodSelect = $('select[name="charges[payment_type]"]');
                const payMethodOption = payMethodSelect.find('option').filter(function() {{
                    return $(this).text().indexOf(paymentMethod) !== -1;
                }}).first();
                if (payMethodOption.length > 0) {{
                    payMethodSelect.selectpicker('val', payMethodOption.val());
                    payMethodSelect.trigger('change');
                }}
            }}""", payment_method)
            time.sleep(0.3)
            logger.info(f"✅ Selected payment method: {payment_method}")
            
            # Fill company expense amount (same as tour charge amount)
            company_amount_input = page.locator('input[name="charges[amount]"]')
            if company_amount_input.count() > 0:
                company_amount_input.fill(str(amount))
                logger.info(f"✅ Filled company amount: {amount}")
            time.sleep(0.3)
            
            # Select payment type (ประเภทจ่าย) - "เบ็ดเตล็ด"
            payment_type = CONFIG.get('payment_type', 'เบ็ดเตล็ด')
            page.evaluate(f"""(paymentType) => {{
                const payTypeSelect = $('select[name="charges[id_company_charges_type]"]');
                const payTypeOption = payTypeSelect.find('option').filter(function() {{
                    return $(this).text().indexOf(paymentType) !== -1;
                }}).first();
                if (payTypeOption.length > 0) {{
                    payTypeSelect.selectpicker('val', payTypeOption.val());
                    payTypeSelect.trigger('change');
                }}
            }}""", payment_type)
            time.sleep(0.3)
            logger.info(f"✅ Selected payment type: {payment_type}")
            
            # Fill payment date (วันที่จ่าย) - same as tour expense payment date
            payment_date = get_payment_date()
            page.evaluate(f"""(date) => {{
                const dateInput = document.querySelector('input[name="charges[payment_date]"]');
                if (dateInput) {{
                    dateInput.value = date;
                    dateInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}
            }}""", payment_date)
            time.sleep(0.3)
            logger.info(f"✅ Filled payment date: {payment_date}")
            
            # Fill period (พีเรียด) - tour code (not program code)
            page.evaluate(f"""(tourCode) => {{
                const periodInput = document.querySelector('input[name="charges[period]"]');
                if (periodInput) {{
                    periodInput.value = tourCode;
                    periodInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}
            }}""", tour_code)
            time.sleep(0.3)
            logger.info(f"✅ Filled period: {tour_code}")
            
            # Fill company expense remark with formatted details
            payment_date = get_payment_date()
            company_remark_text = f"""ค่าใช้จ่ายของบริษัท → {CONFIG['company_name']}
วิธีการจ่าย → {payment_method}
จำนวนเงิน → {amount} THB
ประเภทจ่าย → {payment_type}
วันที่จ่าย → {payment_date}
พีเรียด → {tour_code}"""
            
            company_remark = page.locator('textarea[name="charges[remark]"]')
            if company_remark.count() > 0:
                company_remark.fill(company_remark_text)
                logger.info("✅ Filled company remark")
            time.sleep(0.3)
    
    # STEP 8: Save - using JavaScript to ensure click works
    logger.info("Clicking Save...")
    
    # Scroll the Save button into view and click it using JavaScript
    page.evaluate("""() => {
        const saveBtn = document.querySelector('button[type="submit"], button.btn-primary, input[type="submit"]');
        if (saveBtn) {
            saveBtn.scrollIntoView({ behavior: 'instant', block: 'center' });
            saveBtn.click();
            return true;
        }
        // Try finding any Save button by text
        const buttons = document.querySelectorAll('button');
        for (const btn of buttons) {
            if (btn.textContent.trim() === 'Save') {
                btn.scrollIntoView({ behavior: 'instant', block: 'center' });
                btn.click();
                return true;
            }
        }
        return false;
    }""")
    
    # Wait for response and extract expense number
    try:
        # Wait for navigation or page update
        page.wait_for_timeout(3000)
        
        # Try multiple methods to extract expense number
        expense_no = None
        
        # Method 1: Check the "เลขที่ค่าใช้จ่าย" input field (might be auto-filled after submission)
        expense_no_input = page.evaluate("""() => {
            // Try multiple selectors for the expense number field
            const selectors = [
                'input[name*="charges_no"]',
                'input[name*="expense_no"]',
                'input[placeholder*="C20"]',
                'input[placeholder*="เลขที่"]',
                'input#charges_no',
                'input[name="charges_no"]'
            ];
            
            for (const selector of selectors) {
                const input = document.querySelector(selector);
                if (input && input.value && input.value.match(/C\\d{6}-\\d{6}/)) {
                    return input.value.match(/C\\d{6}-\\d{6}/)[0];
                }
            }
            
            // Also check all inputs with value matching the pattern
            const allInputs = document.querySelectorAll('input[type="text"]');
            for (const input of allInputs) {
                if (input.value && input.value.match(/C\\d{6}-\\d{6}/)) {
                    return input.value.match(/C\\d{6}-\\d{6}/)[0];
                }
            }
            
            return null;
        }""")
        
        if expense_no_input:
            expense_no = expense_no_input
            logger.info(f"📋 Found expense number in input field: {expense_no}")
        
        # Method 2: Look for expense number pattern in page text (format: C202614-139454)
        if not expense_no:
            expense_no_match = page.evaluate("""() => {
                // Look for expense number pattern in page text
                const text = document.body.innerText || document.body.textContent || '';
                const match = text.match(/C\\d{6}-\\d{6}/);
                return match ? match[0] : null;
            }""")
            
            if expense_no_match:
                expense_no = expense_no_match
                logger.info(f"📋 Found expense number in page text: {expense_no}")
        
        # Method 3: Check if redirected to a detail page with expense number in URL
        if not expense_no:
            current_url = page.url
            if '/charges_group/manage/' in current_url or '/charges/manage/' in current_url:
                # Extract from URL if available
                match = re.search(r'/(\d+)$', current_url)
                if match:
                    # Format as CYYMMDD-ID
                    expense_no = f"C{datetime.now().strftime('%y%m%d')}-{match.group(1)}"
                    logger.info(f"📋 Found expense number from URL: {expense_no}")
        
        # Method 4: Check page title or any visible text with the pattern
        if not expense_no:
            expense_no_match = page.evaluate("""() => {
                // Check all text nodes and input values
                const allText = [];
                document.querySelectorAll('*').forEach(el => {
                    if (el.value && el.value.match(/C\\d{6}-\\d{6}/)) {
                        allText.push(el.value.match(/C\\d{6}-\\d{6}/)[0]);
                    }
                    if (el.textContent && el.textContent.match(/C\\d{6}-\\d{6}/)) {
                        allText.push(el.textContent.match(/C\\d{6}-\\d{6}/)[0]);
                    }
                });
                return allText.length > 0 ? allText[0] : null;
            }""")
            
            if expense_no_match:
                expense_no = expense_no_match
                logger.info(f"📋 Found expense number in DOM: {expense_no}")
                
    except Exception as e:
        logger.warning(f"⚠️ Could not extract expense number: {e}")
        expense_no = None
    
    if expense_no:
        logger.info(f"✅ Form submitted for {tour_code} | Expense No: {expense_no}")
    else:
        logger.info(f"✅ Form submitted for {tour_code}")
    
    return expense_no if expense_no else True


def run(start=0, limit=3, headless=False):
    entries = load_csv_data(CONFIG['csv_path'], start, limit)
    logger.info(f"📊 Loaded {len(entries)} entries")
    
    results = []
    program_cache = {}
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, slow_mo=50)
        page = browser.new_page()
        page.set_default_timeout(30000)
        
        login(page)
        
        for i, entry in enumerate(entries):
            tour_code = entry['tour_code']
            pax = entry['pax']
            amount = entry['amount']
            
            logger.info(f"\n{'='*60}")
            logger.info(f"[{i+1}/{len(entries)}] {tour_code} | PAX: {pax} | Amount: {amount}")
            logger.info(f"{'='*60}")
            
            try:
                # Get program code
                prefix_match = re.match(r'^([A-Z0-9]+?)(\d+N)', tour_code)
                prefix = prefix_match.group(1) if prefix_match else tour_code[:5]
                
                if prefix in program_cache:
                    program_code = program_cache[prefix]
                    logger.info(f"📦 Cached: {program_code}")
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
                        'reason': 'No program code',
                        'timestamp': datetime.now().isoformat()
                    })
                    continue
                
                result = fill_form(page, tour_code, program_code, amount, pax)
                # fill_form returns expense_no (string) if successful, True if successful but no expense_no, or False if failed
                success = result is not False and result is not None
                expense_no = result if isinstance(result, str) else None
                
                results.append({
                    'tour_code': tour_code,
                    'program_code': program_code,
                    'pax': pax,
                    'amount': amount,
                    'status': 'SUCCESS' if success else 'FAILED',
                    'expense_no': expense_no if expense_no else '',
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"❌ Error: {e}")
                results.append({
                    'tour_code': entry.get('tour_code', ''),
                    'program_code': '',
                    'pax': entry.get('pax', ''),
                    'amount': entry.get('amount', ''),
                    'status': 'FAILED',
                    'expense_no': '',
                    'reason': str(e)[:100],
                    'timestamp': datetime.now().isoformat()
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
    
    success_count = sum(1 for r in results if r.get('status') == 'SUCCESS')
    logger.info(f"\n📊 SUMMARY: {success_count}/{len(results)} successful")
    logger.info(f"📁 Results: {output_file}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', type=int, default=0)
    parser.add_argument('--limit', type=int, default=3)
    parser.add_argument('--headless', action='store_true')
    parser.add_argument('--all', action='store_true')
    args = parser.parse_args()
    
    run(start=args.start, limit=None if args.all else args.limit, headless=args.headless)
