"""
MCP Server for qualityb2bpackage.com Automation
Provides tools for:
1. Package extraction
2. Expense registration
3. Login management
"""

import asyncio
import json
import logging
import os
import re
import csv
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from playwright.async_api import async_playwright, Browser, Page

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
CONFIG = {
    'username': os.getenv('QB2B_USERNAME', 'noi'),
    'password': os.getenv('QB2B_PASSWORD', 'PrayuthChanocha112'),
    'base_url': 'https://www.qualityb2bpackage.com',
    'login_url': 'https://www.qualityb2bpackage.com/',
    'charges_url': 'https://www.qualityb2bpackage.com/charges_group/create',
    'packages_url': 'https://www.qualityb2bpackage.com/travelpackage',
    'booking_url': 'https://www.qualityb2bpackage.com/booking',
}


class QualityB2BClient:
    """Client for interacting with qualityb2bpackage.com"""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.logged_in = False
        self.playwright = None
    
    async def initialize(self, headless: bool = True):
        """Initialize the browser"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=headless)
        self.page = await self.browser.new_page()
        self.page.set_default_timeout(30000)
        logger.info("Browser initialized")
    
    async def close(self):
        """Close the browser"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Browser closed")
    
    async def login(self) -> bool:
        """Login to the website"""
        try:
            logger.info("Logging in...")
            await self.page.goto(CONFIG['login_url'], wait_until='domcontentloaded')
            await asyncio.sleep(2)
            
            # Check if already logged in
            content = await self.page.content()
            if 'Welcome' in content or 'Dashboard' in content:
                logger.info("Already logged in")
                self.logged_in = True
                return True
            
            # Fill login form
            await self.page.fill('input[type="text"]', CONFIG['username'])
            await self.page.fill('input[type="password"]', CONFIG['password'])
            await self.page.click('button:has-text("Login")')
            await asyncio.sleep(3)
            
            # Verify login
            content = await self.page.content()
            if 'Welcome' in content or 'Dashboard' in content:
                logger.info("✅ Login successful")
                self.logged_in = True
                return True
            else:
                logger.error("❌ Login failed")
                return False
                
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False
    
    async def extract_packages(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Extract tour packages from the website"""
        if not self.logged_in:
            await self.login()
        
        packages = []
        try:
            logger.info("Extracting packages...")
            await self.page.goto(CONFIG['packages_url'], wait_until='domcontentloaded')
            await asyncio.sleep(2)
            
            # Extract package data from table
            packages_data = await self.page.evaluate("""(limit) => {
                const packages = [];
                const rows = document.querySelectorAll('table tbody tr');
                
                for (let i = 0; i < Math.min(rows.length, limit); i++) {
                    const row = rows[i];
                    const cells = row.querySelectorAll('td');
                    
                    if (cells.length >= 6) {
                        // Extract package ID from the link
                        const link = cells[2]?.querySelector('a');
                        const href = link?.getAttribute('href') || '';
                        const idMatch = href.match(/manage\\/([0-9]+)/);
                        const packageId = idMatch ? idMatch[1] : '';
                        
                        packages.push({
                            id: packageId,
                            code: cells[1]?.innerText?.trim() || '',
                            name: cells[2]?.innerText?.trim() || '',
                            format: cells[3]?.innerText?.trim() || '',
                            category: cells[4]?.innerText?.trim() || '',
                            expiry: cells[5]?.innerText?.trim() || '',
                            created: cells[6]?.innerText?.trim() || '',
                            edited: cells[7]?.innerText?.trim() || '',
                        });
                    }
                }
                return packages;
            }""", limit)
            
            packages = packages_data
            logger.info(f"✅ Extracted {len(packages)} packages")
            
        except Exception as e:
            logger.error(f"Package extraction error: {e}")
        
        return packages
    
    async def get_package_details(self, package_id: str) -> Dict[str, Any]:
        """Get detailed information for a specific package"""
        if not self.logged_in:
            await self.login()
        
        details = {}
        try:
            url = f"{CONFIG['base_url']}/travelpackage/manage/{package_id}"
            await self.page.goto(url, wait_until='domcontentloaded')
            await asyncio.sleep(2)
            
            # Extract details using JavaScript
            details = await self.page.evaluate("""() => {
                const getValue = (selector) => {
                    const el = document.querySelector(selector);
                    return el ? (el.value || el.innerText || '').trim() : '';
                };
                
                const getSelectValue = (selector) => {
                    const el = document.querySelector(selector);
                    if (el && el.tagName === 'SELECT') {
                        return el.options[el.selectedIndex]?.text || '';
                    }
                    // For Bootstrap selectpicker
                    const btn = document.querySelector(selector + ' + .dropdown-toggle');
                    return btn ? btn.innerText.trim() : getValue(selector);
                };
                
                return {
                    program_code: getValue('#program_code'),
                    program_name: getValue('#program_name'),
                    short_detail: getValue('#short_detail'),
                    num_schedules: getValue('#num_program'),
                    country: getSelectValue('select[name="country[]"]'),
                    province: getSelectValue('select[name="province[]"]'),
                };
            }""")
            
            details['id'] = package_id
            logger.info(f"✅ Got details for package {package_id}")
            
        except Exception as e:
            logger.error(f"Error getting package details: {e}")
        
        return details
    
    async def find_program_code(self, tour_code: str) -> Optional[str]:
        """Find program code from tour code"""
        if not self.logged_in:
            await self.login()
        
        try:
            logger.info(f"🔍 Searching for program code: {tour_code}")
            await self.page.goto(CONFIG['packages_url'], wait_until='domcontentloaded')
            await asyncio.sleep(2)
            
            # Search for the tour code
            search_input = await self.page.query_selector('input[placeholder*="keyword"], input[placeholder*="ชื่อโปรแกรม"]')
            if search_input:
                await search_input.fill(tour_code)
                await self.page.click('button:has-text("Go!")')
                await asyncio.sleep(3)
            
            # Extract program code from results
            content = await self.page.content()
            prefix_match = re.match(r'^([A-Z0-9]+?)(\d+N)', tour_code)
            prefix = prefix_match.group(1) if prefix_match else tour_code[:5]
            
            pattern = rf'{prefix}-[A-Z]{{2}}\d{{3}}'
            matches = re.findall(pattern, content)
            
            if matches:
                logger.info(f"✅ Found program code: {matches[0]}")
                return matches[0]
            
            logger.warning("⚠️ Program code not found")
            return None
            
        except Exception as e:
            logger.error(f"Error finding program code: {e}")
            return None
    
    async def create_expense(
        self,
        tour_code: str,
        program_code: str,
        amount: int,
        pax: int,
        description: str = "ค่าอุปกรณ์ออกทัวร์",
        charge_type: str = "ค่าใช้จ่ายเบ็ดเตล็ด",
        add_company_expense: bool = True,
        company_value: str = "39",
        payment_method: str = "โอนเข้าบัญชี",
        payment_type: str = "เบ็ดเตล็ด"
    ) -> Dict[str, Any]:
        """Create an expense record with proper form submission"""
        if not self.logged_in:
            await self.login()
        
        result = {
            'success': False,
            'tour_code': tour_code,
            'program_code': program_code,
            'amount': amount,
            'expense_no': None,
            'error': None
        }
        
        try:
            logger.info(f"📝 Creating expense: {tour_code} | {program_code} | {amount}")
            await self.page.goto(CONFIG['charges_url'], wait_until='domcontentloaded')
            await asyncio.sleep(3)
            
            # STEP 1: Set date range to include more programs
            logger.info("Setting date range...")
            await self.page.evaluate("""() => {
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
            await asyncio.sleep(3)
            
            # STEP 2: Select program using jQuery selectpicker
            logger.info(f"Selecting program: {program_code}")
            select_result = await self.page.evaluate(f"""(programCode) => {{
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
            
            program_full_name = ""
            if select_result.get('success'):
                program_full_name = select_result.get('text', program_code)
                logger.info(f"✅ Program selected: {program_full_name}")
            else:
                logger.warning(f"⚠️ Program not found: {select_result.get('error')}")
            await asyncio.sleep(2)
            
            # STEP 3: Select tour code
            logger.info(f"Selecting tour code: {tour_code}")
            tour_result = await self.page.evaluate(f"""(tourCode) => {{
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
            await asyncio.sleep(1)
            
            # STEP 4: Fill form fields
            payment_date = (datetime.now() + timedelta(days=7)).strftime("%d/%m/%Y")
            
            logger.info("Filling form fields...")
            await self.page.evaluate(f"""() => {{
                // Payment date
                const dateInput = document.querySelector('input[name="payment_date"]');
                if (dateInput) {{
                    dateInput.value = '{payment_date}';
                    dateInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}
                
                // Description
                const descInput = document.querySelector('input[name="description[]"]');
                if (descInput) descInput.value = '{description}';
                
                // Charge type using selectpicker
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
            await asyncio.sleep(0.5)
            
            # STEP 5: Fill remark
            remark_text = f"""เลขที่ : 
Program : {program_full_name}
Code Program : {program_code}
Code group : {tour_code}

รายละเอียด : 
{description} 50 (Fixed) x {pax} PAX = {amount} THB (Auto calculate)

ยอดเงินรวม : {amount} THB

วันจ่าย : {payment_date}"""
            
            remark_input = self.page.locator('textarea[name="remark"]')
            if await remark_input.count() > 0:
                await remark_input.fill(remark_text)
                logger.info("✅ Filled tour expense remark")
            await asyncio.sleep(0.3)
            
            # STEP 6: Add company expense if enabled
            if add_company_expense:
                logger.info("📋 Adding company expense...")
                company_toggle = self.page.locator('text=เพิ่มในค่าใช้จ่ายบริษัท').first
                if await company_toggle.count() > 0:
                    await company_toggle.click()
                    await asyncio.sleep(1)
                    
                    # Select company
                    await self.page.evaluate(f"""() => {{
                        const companySelect = $('select[name="charges[id_company_charges_agent]"]');
                        companySelect.selectpicker('val', '{company_value}');
                        companySelect.trigger('change');
                    }}""")
                    await asyncio.sleep(0.5)
                    
                    # Select payment method
                    await self.page.evaluate(f"""(paymentMethod) => {{
                        const payMethodSelect = $('select[name="charges[payment_type]"]');
                        const payMethodOption = payMethodSelect.find('option').filter(function() {{
                            return $(this).text().indexOf(paymentMethod) !== -1;
                        }}).first();
                        if (payMethodOption.length > 0) {{
                            payMethodSelect.selectpicker('val', payMethodOption.val());
                            payMethodSelect.trigger('change');
                        }}
                    }}""", payment_method)
                    await asyncio.sleep(0.3)
                    
                    # Fill company amount
                    company_amount_input = self.page.locator('input[name="charges[amount]"]')
                    if await company_amount_input.count() > 0:
                        await company_amount_input.fill(str(amount))
                    await asyncio.sleep(0.3)
                    
                    # Select payment type
                    await self.page.evaluate(f"""(paymentType) => {{
                        const payTypeSelect = $('select[name="charges[id_company_charges_type]"]');
                        const payTypeOption = payTypeSelect.find('option').filter(function() {{
                            return $(this).text().indexOf(paymentType) !== -1;
                        }}).first();
                        if (payTypeOption.length > 0) {{
                            payTypeSelect.selectpicker('val', payTypeOption.val());
                            payTypeSelect.trigger('change');
                        }}
                    }}""", payment_type)
                    await asyncio.sleep(0.3)
                    
                    # Fill payment date
                    await self.page.evaluate(f"""(date) => {{
                        const dateInput = document.querySelector('input[name="charges[payment_date]"]');
                        if (dateInput) {{
                            dateInput.value = date;
                            dateInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        }}
                    }}""", payment_date)
                    await asyncio.sleep(0.3)
                    
                    # Fill period
                    await self.page.evaluate(f"""(tourCode) => {{
                        const periodInput = document.querySelector('input[name="charges[period]"]');
                        if (periodInput) {{
                            periodInput.value = tourCode;
                            periodInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        }}
                    }}""", tour_code)
                    await asyncio.sleep(0.3)
                    
                    # Fill company remark
                    company_remark_text = f"""ค่าใช้จ่ายของบริษัท → GO365 TRAVEL CO.,LTD.
วิธีการจ่าย → {payment_method}
จำนวนเงิน → {amount} THB
ประเภทจ่าย → {payment_type}
วันที่จ่าย → {payment_date}
พีเรียด → {tour_code}"""
                    
                    company_remark = self.page.locator('textarea[name="charges[remark]"]')
                    if await company_remark.count() > 0:
                        await company_remark.fill(company_remark_text)
                    await asyncio.sleep(0.3)
            
            # STEP 7: Submit the form - FIXED: Use correct selector for input[type="submit"]
            logger.info("Submitting form...")
            
            # Method 1: Click the submit button directly
            submit_btn = self.page.locator('input[type="submit"][value="Save"]')
            if await submit_btn.count() > 0:
                await submit_btn.scroll_into_view_if_needed()
                await asyncio.sleep(0.5)
                await submit_btn.click()
                logger.info("✅ Clicked Save button")
            else:
                # Fallback: Use JavaScript to submit
                await self.page.evaluate("""() => {
                    const form = document.querySelector('form');
                    if (form) {
                        form.submit();
                        return true;
                    }
                    // Try clicking any save button
                    const saveBtn = document.querySelector('input[type="submit"], button[type="submit"]');
                    if (saveBtn) {
                        saveBtn.click();
                        return true;
                    }
                    return false;
                }""")
                logger.info("✅ Form submitted via JavaScript")
            
            # Wait for response
            await asyncio.sleep(3)
            
            # Try to extract expense number
            expense_no = await self._extract_expense_number()
            
            result['success'] = True
            result['expense_no'] = expense_no
            logger.info(f"✅ Expense created: {expense_no or 'No number returned'}")
            
        except Exception as e:
            logger.error(f"❌ Error creating expense: {e}")
            result['error'] = str(e)
        
        return result
    
    async def _extract_expense_number(self) -> Optional[str]:
        """Extract expense number from the page after submission"""
        try:
            # Method 1: Check input field
            expense_no = await self.page.evaluate("""() => {
                const selectors = [
                    'input[name*="charges_no"]',
                    'input[name*="expense_no"]',
                    'input[placeholder*="C20"]',
                    'input#charges_no'
                ];
                
                for (const selector of selectors) {
                    const input = document.querySelector(selector);
                    if (input && input.value && input.value.match(/C\\d{6}-\\d{6}/)) {
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
            current_url = self.page.url
            if '/charges_group/manage/' in current_url or '/charges/manage/' in current_url:
                match = re.search(r'/(\d+)$', current_url)
                if match:
                    return f"C{datetime.now().strftime('%y%m%d')}-{match.group(1)}"
            
            return None
            
        except Exception as e:
            logger.warning(f"Could not extract expense number: {e}")
            return None


async def main():
    """Test the client"""
    client = QualityB2BClient()
    
    try:
        await client.initialize(headless=False)
        await client.login()
        
        # Test package extraction
        packages = await client.extract_packages(limit=5)
        print(f"\nExtracted {len(packages)} packages:")
        for pkg in packages:
            print(f"  - {pkg.get('code')}: {pkg.get('name')[:50]}...")
        
        # Test expense creation (commented out for safety)
        # result = await client.create_expense(
        #     tour_code="TEST123",
        #     program_code="TEST-CODE",
        #     amount=1000,
        #     pax=10
        # )
        # print(f"\nExpense result: {result}")
        
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
