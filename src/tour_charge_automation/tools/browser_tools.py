"""
Custom Browser Automation Tools for CrewAI Agents
Provides Playwright-based tools for web automation tasks.
"""

import os
import re
import time
import logging
from datetime import datetime, timedelta
from typing import Optional, Type, Any
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class BrowserManager:
    """
    Singleton manager for browser instance to share across tools.
    Ensures all tools use the same browser session.
    """
    _instance = None
    _browser: Optional[Browser] = None
    _context: Optional[BrowserContext] = None
    _page: Optional[Page] = None
    _playwright = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_page(self, headless: bool = False) -> Page:
        """Get or create the browser page."""
        if self._page is None or self._page.is_closed():
            if self._playwright is None:
                self._playwright = sync_playwright().start()
            if self._browser is None:
                self._browser = self._playwright.chromium.launch(headless=headless, slow_mo=50)
            if self._context is None:
                self._context = self._browser.new_context()
            self._page = self._context.new_page()
            self._page.set_default_timeout(30000)
        return self._page
    
    def close(self):
        """Close all browser resources."""
        if self._page and not self._page.is_closed():
            self._page.close()
        if self._context:
            self._context.close()
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()
        self._page = None
        self._context = None
        self._browser = None
        self._playwright = None


# Tool Input Schemas
class LoginInput(BaseModel):
    """Input for login tool."""
    username: str = Field(default=None, description="Username for login")
    password: str = Field(default=None, description="Password for login")


class FindProgramCodeInput(BaseModel):
    """Input for finding program code."""
    tour_code: str = Field(description="The tour code to search for (e.g., G8HRB5NHRBCZ250103)")


class NavigateToFormInput(BaseModel):
    """Input for navigating to form."""
    url: str = Field(default=None, description="URL to navigate to")


class FillFormInput(BaseModel):
    """Input for filling the expense form."""
    tour_code: str = Field(description="The tour code (e.g., G8HRB5NHRBCZ250103)")
    program_code: str = Field(description="The program code (e.g., G8HRB-CZ001)")
    amount: float = Field(description="The expense amount in THB")
    pax: int = Field(description="Number of passengers")


class ExtractExpenseNumberInput(BaseModel):
    """Input for extracting expense number."""
    pass


# CrewAI Tools
class LoginTool(BaseTool):
    """Tool for logging into the QualityB2BPackage system."""
    name: str = "login_to_system"
    description: str = "Log in to the QualityB2BPackage website. Use this before any other browser actions."
    args_schema: Type[BaseModel] = LoginInput
    
    def _run(self, username: str = None, password: str = None) -> str:
        """Execute the login."""
        try:
            from dotenv import load_dotenv
            load_dotenv()
            
            username = username or os.getenv("WEBSITE_USERNAME", "noi")
            password = password or os.getenv("WEBSITE_PASSWORD", "PrayuthChanocha112")
            
            browser_manager = BrowserManager()
            page = browser_manager.get_page(headless=False)
            
            logger.info("🔐 Logging in...")
            page.goto("https://www.qualityb2bpackage.com/")
            page.wait_for_load_state("networkidle")
            
            # Fill login form
            page.fill("input[type='text']", username)
            page.fill("input[type='password']", password)
            page.click("button:has-text('Login')")
            
            # Wait for login to complete
            page.wait_for_load_state("networkidle")
            time.sleep(2)
            
            # Verify login success
            if "logout" in page.content().lower() or "dashboard" in page.url.lower():
                logger.info("✅ Logged in successfully")
                return "Successfully logged into QualityB2BPackage system."
            else:
                return "Login completed but could not verify success. Please check manually."
                
        except Exception as e:
            logger.error(f"❌ Login failed: {e}")
            return f"Login failed: {str(e)}"


class FindProgramCodeTool(BaseTool):
    """Tool for finding program code from tour code."""
    name: str = "find_program_code"
    description: str = "Search the QualityB2BPackage system to find the program code for a given tour code."
    args_schema: Type[BaseModel] = FindProgramCodeInput
    
    def _run(self, tour_code: str) -> str:
        """Find the program code for a tour code."""
        try:
            browser_manager = BrowserManager()
            page = browser_manager.get_page()
            
            logger.info(f"🔍 Searching for program code: {tour_code}")
            
            # Navigate to search page
            page.goto("https://www.qualityb2bpackage.com/travelpackage")
            page.wait_for_load_state("networkidle")
            
            # Search for tour code
            search_input = page.locator("input[placeholder*='keyword'], input[name='keyword'], input.search")
            if search_input.count() > 0:
                search_input.first.fill(tour_code)
            
            # Click search button
            search_btn = page.locator("button:has-text('Go'), button:has-text('Search'), button[type='submit']")
            if search_btn.count() > 0:
                search_btn.first.click()
            
            page.wait_for_load_state("networkidle")
            time.sleep(2)
            
            # Extract program code from results
            content = page.content()
            
            # Try multiple patterns
            patterns = [
                rf'({tour_code[:5]}-[A-Z]{{2}}\d{{3}})',  # e.g., G8HRB-CZ001
                r'([A-Z0-9]{5}-[A-Z]{2}\d{3})',  # General pattern
                rf'data-program[^>]*>([^<]*{tour_code[:5]}[^<]*)<'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, content)
                if match:
                    program_code = match.group(1)
                    logger.info(f"✅ Found program code: {program_code}")
                    return f"Program code found: {program_code}"
            
            # Fallback: derive from tour code
            prefix = tour_code[:5]  # e.g., G8HRB
            # Try to find airline code in tour code
            airline_match = re.search(r'([A-Z]{2})(\d{6})$', tour_code)
            if airline_match:
                airline = airline_match.group(1)
                program_code = f"{prefix}-{airline}001"
                logger.info(f"⚠️ Derived program code: {program_code}")
                return f"Program code derived: {program_code}"
            
            return f"Could not find program code for tour code: {tour_code}"
            
        except Exception as e:
            logger.error(f"❌ Error finding program code: {e}")
            return f"Error finding program code: {str(e)}"


class NavigateToFormTool(BaseTool):
    """Tool for navigating to the charges form."""
    name: str = "navigate_to_charges_form"
    description: str = "Navigate to the charges group creation form page."
    args_schema: Type[BaseModel] = NavigateToFormInput
    
    def _run(self, url: str = None) -> str:
        """Navigate to the form page."""
        try:
            from dotenv import load_dotenv
            load_dotenv()
            
            url = url or os.getenv("WEBSITE_CHARGES_FORM_URL", "https://www.qualityb2bpackage.com/charges_group/create")
            
            browser_manager = BrowserManager()
            page = browser_manager.get_page()
            
            logger.info(f"📄 Navigating to charges form: {url}")
            page.goto(url)
            page.wait_for_load_state("networkidle")
            time.sleep(2)
            
            # Verify we're on the right page
            if "create" in page.url or "charges" in page.url:
                logger.info("✅ Successfully navigated to charges form")
                return f"Successfully navigated to charges form at {page.url}"
            else:
                return f"Navigation completed but ended up at {page.url}"
                
        except Exception as e:
            logger.error(f"❌ Navigation failed: {e}")
            return f"Navigation failed: {str(e)}"


class FillFormTool(BaseTool):
    """Tool for filling and submitting the expense form."""
    name: str = "fill_expense_form"
    description: str = "Fill out and submit the tour charge expense form with the provided data."
    args_schema: Type[BaseModel] = FillFormInput
    
    def _get_payment_date(self) -> str:
        """Get payment date (7 days from now)."""
        return (datetime.now() + timedelta(days=7)).strftime("%d/%m/%Y")
    
    def _generate_remark(self, program_code: str, tour_code: str, pax: int, amount: float) -> str:
        """Generate the remark text for the expense."""
        payment_date = self._get_payment_date()
        return f"""เลขที่ : 
Program : {program_code}
Code Program : {program_code}
Code group : {tour_code}
รายละเอียด : ค่าอุปกรณ์ออกทัวร์ 50 (Fixed) x {pax} PAX = {int(amount)} THB
ยอดเงินรวม : {int(amount)} THB
วันจ่าย : {payment_date}"""
    
    def _generate_company_remark(self, company_name: str, payment_method: str, 
                                  amount: float, payment_type: str, 
                                  payment_date: str, tour_code: str) -> str:
        """Generate company expense remark."""
        return f"""ค่าใช้จ่ายของบริษัท → {company_name}
วิธีการจ่าย → {payment_method}
จำนวนเงิน → {int(amount)} THB
ประเภทจ่าย → {payment_type}
วันที่จ่าย → {payment_date}
พีเรียด → {tour_code}"""
    
    def _run(self, tour_code: str, program_code: str, amount: float, pax: int) -> str:
        """Fill and submit the expense form."""
        try:
            from dotenv import load_dotenv
            load_dotenv()
            
            browser_manager = BrowserManager()
            page = browser_manager.get_page()
            
            logger.info(f"📝 Filling form: {tour_code} | {program_code} | Amount: {amount} | PAX: {pax}")
            
            # Navigate to form if not already there
            if "create" not in page.url:
                page.goto("https://www.qualityb2bpackage.com/charges_group/create")
                page.wait_for_load_state("networkidle")
                time.sleep(2)
            
            # STEP 1: Set date range
            date_start = os.getenv("DATE_START", "01/01/2024")
            date_end = os.getenv("DATE_END", "31/12/2026")
            
            page.evaluate(f"""() => {{
                const startInput = document.querySelector('input[name="start"]');
                const endInput = document.querySelector('input[name="end"]');
                if (startInput) {{
                    startInput.value = '{date_start}';
                    startInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}
                if (endInput) {{
                    endInput.value = '{date_end}';
                    endInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}
            }}""")
            time.sleep(1)
            logger.info(f"✅ Date range set: {date_start} - {date_end}")
            
            # STEP 2: Select Program
            page.evaluate(f"""(programCode) => {{
                const packageSelect = $('select[name="package"]');
                const option = packageSelect.find('option').filter(function() {{
                    return $(this).text().indexOf(programCode) !== -1;
                }}).first();
                if (option.length > 0) {{
                    packageSelect.selectpicker('val', option.val());
                    packageSelect.trigger('change');
                }}
            }}""", program_code)
            time.sleep(3)
            logger.info(f"✅ Program selected: {program_code}")
            
            # STEP 3: Select Tour Code
            page.evaluate(f"""(tourCode) => {{
                const groupSelect = $('select[name="group_code_package"]');
                const option = groupSelect.find('option').filter(function() {{
                    return $(this).text().indexOf(tourCode) !== -1;
                }}).first();
                if (option.length > 0) {{
                    groupSelect.selectpicker('val', option.val());
                    groupSelect.trigger('change');
                }}
            }}""", tour_code)
            time.sleep(2)
            logger.info(f"✅ Tour code selected: {tour_code}")
            
            # STEP 4: Fill expense fields
            payment_date = self._get_payment_date()
            description = os.getenv("DESCRIPTION", "ค่าอุปกรณ์ออกทัวร์")
            
            page.evaluate(f"""() => {{
                // Payment date
                const paymentDateInput = document.querySelector('input[name="payment_date"]');
                if (paymentDateInput) {{
                    paymentDateInput.value = '{payment_date}';
                    paymentDateInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}
                
                // Description
                const descInput = document.querySelector('input[name="description[]"]');
                if (descInput) descInput.value = '{description}';
                
                // Amount
                const priceInput = document.querySelector('input[name="price[]"]');
                if (priceInput) priceInput.value = '{int(amount)}';
            }}""")
            time.sleep(0.5)
            
            # Select charge type
            page.evaluate("""() => {
                const typeSelect = $('select[name="rate_type[]"]');
                const option = typeSelect.find('option').filter(function() {
                    return $(this).text().indexOf('เบ็ดเตล็ด') !== -1;
                }).first();
                if (option.length > 0) {
                    typeSelect.selectpicker('val', option.val());
                    typeSelect.trigger('change');
                }
            }""")
            time.sleep(0.5)
            
            # Fill main remark
            remark_text = self._generate_remark(program_code, tour_code, pax, amount)
            remark_field = page.locator('textarea[name="remark"]')
            if remark_field.count() > 0:
                remark_field.fill(remark_text)
            logger.info("✅ Filled tour expense fields")
            
            # STEP 5: Add company expense
            company_name = os.getenv("COMPANY_NAME", "GO365 TRAVEL CO.,LTD.")
            company_value = os.getenv("COMPANY_VALUE", "39")
            payment_method = os.getenv("PAYMENT_METHOD", "โอนเข้าบัญชี")
            payment_type = os.getenv("PAYMENT_TYPE", "เบ็ดเตล็ด")
            
            # Click toggle to enable company expense
            toggle = page.locator('text=เพิ่มในค่าใช้จ่ายบริษัท')
            if toggle.count() > 0:
                toggle.first.click()
                time.sleep(1)
            
            # Select company
            page.evaluate(f"""(companyValue) => {{
                const companySelect = $('select[name="charges[id_company_charges_agent]"]');
                if (companySelect.length > 0) {{
                    companySelect.selectpicker('val', companyValue);
                    companySelect.trigger('change');
                }}
            }}""", company_value)
            time.sleep(0.5)
            logger.info(f"✅ Selected company: {company_name}")
            
            # Select payment method
            page.evaluate(f"""(method) => {{
                const methodSelect = $('select[name="charges[payment_type]"]');
                const option = methodSelect.find('option').filter(function() {{
                    return $(this).text().indexOf(method) !== -1;
                }}).first();
                if (option.length > 0) {{
                    methodSelect.selectpicker('val', option.val());
                    methodSelect.trigger('change');
                }}
            }}""", payment_method)
            time.sleep(0.3)
            logger.info(f"✅ Selected payment method: {payment_method}")
            
            # Fill company amount
            company_amount_field = page.locator('input[name="charges[amount]"]')
            if company_amount_field.count() > 0:
                company_amount_field.fill(str(int(amount)))
            logger.info(f"✅ Filled company amount: {amount}")
            
            # Select payment type
            page.evaluate(f"""(paymentType) => {{
                const typeSelect = $('select[name="charges[id_company_charges_type]"]');
                const option = typeSelect.find('option').filter(function() {{
                    return $(this).text().indexOf(paymentType) !== -1;
                }}).first();
                if (option.length > 0) {{
                    typeSelect.selectpicker('val', option.val());
                    typeSelect.trigger('change');
                }}
            }}""", payment_type)
            time.sleep(0.3)
            logger.info(f"✅ Selected payment type: {payment_type}")
            
            # Fill company payment date
            page.evaluate(f"""(date) => {{
                const dateInput = document.querySelector('input[name="charges[payment_date]"]');
                if (dateInput) {{
                    dateInput.value = date;
                    dateInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}
            }}""", payment_date)
            time.sleep(0.3)
            logger.info(f"✅ Filled payment date: {payment_date}")
            
            # Fill period (tour code)
            page.evaluate(f"""(tourCode) => {{
                const periodInput = document.querySelector('input[name="charges[period]"]');
                if (periodInput) {{
                    periodInput.value = tourCode;
                    periodInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}
            }}""", tour_code)
            time.sleep(0.3)
            logger.info(f"✅ Filled period: {tour_code}")
            
            # Fill company remark
            company_remark = self._generate_company_remark(
                company_name, payment_method, amount, payment_type, payment_date, tour_code
            )
            company_remark_field = page.locator('textarea[name="charges[remark]"]')
            if company_remark_field.count() > 0:
                company_remark_field.fill(company_remark)
            logger.info("✅ Filled company remark")
            
            # STEP 6: Submit form
            logger.info("🚀 Submitting form...")
            page.evaluate("""() => {
                const saveBtn = document.querySelector('button[type="submit"], button.btn-primary, input[type="submit"]');
                if (saveBtn) {
                    saveBtn.scrollIntoView({ behavior: 'instant', block: 'center' });
                    saveBtn.click();
                    return true;
                }
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
            
            time.sleep(3)
            logger.info(f"✅ Form submitted for {tour_code}")
            
            return f"Successfully filled and submitted expense form for tour code: {tour_code}"
            
        except Exception as e:
            logger.error(f"❌ Error filling form: {e}")
            return f"Error filling form: {str(e)}"


class ExtractExpenseNumberTool(BaseTool):
    """Tool for extracting expense number after submission."""
    name: str = "extract_expense_number"
    description: str = "Extract the expense order number from the page after form submission."
    args_schema: Type[BaseModel] = ExtractExpenseNumberInput
    
    def _run(self) -> str:
        """Extract the expense number from the current page."""
        try:
            browser_manager = BrowserManager()
            page = browser_manager.get_page()
            
            logger.info("🔍 Extracting expense number...")
            
            # Wait for any page updates
            time.sleep(2)
            
            expense_no = None
            
            # Method 1: Look for pattern in input fields
            expense_no = page.evaluate("""() => {
                const allInputs = document.querySelectorAll('input[type="text"]');
                for (const input of allInputs) {
                    if (input.value && input.value.match(/C\\d{6}-\\d{6}/)) {
                        return input.value.match(/C\\d{6}-\\d{6}/)[0];
                    }
                }
                return null;
            }""")
            
            if expense_no:
                logger.info(f"✅ Found expense number in input: {expense_no}")
                return f"Expense number: {expense_no}"
            
            # Method 2: Look for pattern in page text
            expense_no = page.evaluate("""() => {
                const text = document.body.innerText || document.body.textContent || '';
                const match = text.match(/C\\d{6}-\\d{6}/);
                return match ? match[0] : null;
            }""")
            
            if expense_no:
                logger.info(f"✅ Found expense number in page: {expense_no}")
                return f"Expense number: {expense_no}"
            
            # Method 3: Check URL for ID
            current_url = page.url
            if '/manage/' in current_url or '/view/' in current_url:
                match = re.search(r'/(\d+)$', current_url)
                if match:
                    expense_no = f"C{datetime.now().strftime('%y%m%d')}-{match.group(1)}"
                    logger.info(f"✅ Derived expense number from URL: {expense_no}")
                    return f"Expense number (from URL): {expense_no}"
            
            logger.warning("⚠️ Could not find expense number")
            return "Expense number not found. The form may have been submitted successfully but the number was not displayed."
            
        except Exception as e:
            logger.error(f"❌ Error extracting expense number: {e}")
            return f"Error extracting expense number: {str(e)}"
