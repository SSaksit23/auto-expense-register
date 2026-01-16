"""
Package Extractor for qualityb2bpackage.com
Extracts tour package data and exports to CSV/JSON
"""

import asyncio
import json
import csv
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright, Browser, Page

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
CONFIG = {
    'username': 'noi',
    'password': 'PrayuthChanocha112',
    'base_url': 'https://www.qualityb2bpackage.com',
    'login_url': 'https://www.qualityb2bpackage.com/',
    'packages_url': 'https://www.qualityb2bpackage.com/travelpackage',
}


class PackageExtractor:
    """Extract tour packages from qualityb2bpackage.com"""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self.logged_in = False
    
    async def initialize(self, headless: bool = True):
        """Initialize browser"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=headless)
        self.page = await self.browser.new_page()
        self.page.set_default_timeout(30000)
        logger.info("Browser initialized")
    
    async def close(self):
        """Close browser"""
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
            
            # Fill login form
            await self.page.fill('input[type="text"]', CONFIG['username'])
            await self.page.fill('input[type="password"]', CONFIG['password'])
            await self.page.click('button:has-text("Login")')
            await asyncio.sleep(3)
            
            # Verify login by trying to access a protected page
            await self.page.goto(CONFIG['packages_url'], wait_until='domcontentloaded')
            await asyncio.sleep(2)
            
            # If we can see the packages table, login was successful
            has_table = await self.page.query_selector('table')
            if has_table:
                logger.info("✅ Login successful")
                self.logged_in = True
                return True
            
            logger.error("Login failed - could not access protected page")
            return False
            
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False
    
    async def extract_package_list(
        self,
        filters: Optional[Dict[str, str]] = None,
        max_pages: int = 10
    ) -> List[Dict[str, Any]]:
        """Extract list of packages with optional filters"""
        if not self.logged_in:
            await self.login()
        
        all_packages = []
        
        try:
            await self.page.goto(CONFIG['packages_url'], wait_until='domcontentloaded')
            await asyncio.sleep(2)
            
            # Apply filters if provided
            if filters:
                if 'country' in filters:
                    await self._select_dropdown('select[name="country"]', filters['country'])
                if 'city' in filters:
                    await self._select_dropdown('select[name="city"]', filters['city'])
                if 'keyword' in filters:
                    await self.page.fill('#input_search', filters['keyword'])
                    await self.page.click('button:has-text("Go!")')
                    await asyncio.sleep(2)
            
            # Extract packages from current page
            page_num = 1
            while page_num <= max_pages:
                logger.info(f"Extracting page {page_num}...")
                
                packages = await self._extract_packages_from_page()
                if not packages:
                    break
                
                all_packages.extend(packages)
                
                # Try to go to next page
                next_btn = await self.page.query_selector('a.page-link:has-text("Next"), a.page-link:has-text(">")')
                if next_btn:
                    await next_btn.click()
                    await asyncio.sleep(2)
                    page_num += 1
                else:
                    break
            
            logger.info(f"✅ Extracted {len(all_packages)} packages total")
            
        except Exception as e:
            logger.error(f"Extraction error: {e}")
        
        return all_packages
    
    async def _extract_packages_from_page(self) -> List[Dict[str, Any]]:
        """Extract packages from current page"""
        return await self.page.evaluate("""() => {
            const packages = [];
            // Get all rows from the table (skip header row)
            const rows = document.querySelectorAll('table tr');
            
            for (let i = 1; i < rows.length; i++) {
                const row = rows[i];
                const cells = row.querySelectorAll('td');
                
                if (cells.length >= 6) {
                    // Get status from ON/OFF badge in first cell
                    const statusBadge = cells[0]?.querySelector('.badge, span');
                    const status = statusBadge?.innerText?.trim() || '';
                    
                    // Get package ID from second cell
                    const packageId = cells[1]?.innerText?.trim() || '';
                    
                    // Get package link and name from third cell
                    const link = cells[2]?.querySelector('a');
                    const href = link?.getAttribute('href') || '';
                    const name = cells[2]?.innerText?.trim() || '';
                    
                    packages.push({
                        id: packageId,
                        status: status,
                        code: packageId,
                        name: name,
                        format: cells[3]?.innerText?.trim() || '',
                        category: cells[4]?.innerText?.trim() || '',
                        expiry: cells[5]?.innerText?.trim() || '',
                        created: cells[6]?.innerText?.trim() || '',
                        edited: cells[7]?.innerText?.trim() || '',
                        url: href ? 'https://www.qualityb2bpackage.com' + href : ''
                    });
                }
            }
            
            return packages;
        }""")
    
    async def _select_dropdown(self, selector: str, value: str):
        """Select value in a Bootstrap selectpicker dropdown"""
        await self.page.evaluate(f"""(selector, value) => {{
            const select = $(selector);
            const option = select.find('option').filter(function() {{
                return $(this).text().indexOf(value) !== -1;
            }}).first();
            if (option.length > 0) {{
                select.selectpicker('val', option.val());
                select.trigger('change');
            }}
        }}""", selector, value)
        await asyncio.sleep(1)
    
    async def get_package_details(self, package_id: str) -> Dict[str, Any]:
        """Get detailed information for a specific package"""
        if not self.logged_in:
            await self.login()
        
        details = {'id': package_id}
        
        try:
            url = f"{CONFIG['base_url']}/travelpackage/manage/{package_id}"
            await self.page.goto(url, wait_until='domcontentloaded')
            await asyncio.sleep(2)
            
            # Extract basic info
            details.update(await self.page.evaluate("""() => {
                const getValue = (selector) => {
                    const el = document.querySelector(selector);
                    return el ? (el.value || el.innerText || '').trim() : '';
                };
                
                const getChecked = (name) => {
                    const checked = document.querySelector(`input[name="${name}"]:checked`);
                    return checked ? checked.nextElementSibling?.innerText?.trim() || checked.value : '';
                };
                
                return {
                    program_code: getValue('#program_code'),
                    program_name: getValue('#program_name'),
                    short_detail: getValue('#short_detail'),
                    num_schedules: getValue('#num_program'),
                    tour_type: getChecked('type_program'),
                    web_display: getChecked('status'),
                };
            }"""))
            
            # Extract country/city info from selectpickers
            location_info = await self.page.evaluate("""() => {
                const getSelectText = (selector) => {
                    const btn = document.querySelector(selector + ' + button.dropdown-toggle');
                    return btn ? btn.innerText.trim() : '';
                };
                
                return {
                    country: getSelectText('select[name="country[]"]'),
                    province: getSelectText('select[name="province[]"]'),
                    main_city: getSelectText('select[name="main_city"]'),
                };
            }""")
            details.update(location_info)
            
            logger.info(f"✅ Got details for package {package_id}: {details.get('program_code')}")
            
        except Exception as e:
            logger.error(f"Error getting details for {package_id}: {e}")
            details['error'] = str(e)
        
        return details
    
    async def extract_all_with_details(
        self,
        filters: Optional[Dict[str, str]] = None,
        max_packages: int = 50
    ) -> List[Dict[str, Any]]:
        """Extract packages with full details"""
        packages = await self.extract_package_list(filters, max_pages=10)
        packages = packages[:max_packages]
        
        detailed_packages = []
        for i, pkg in enumerate(packages):
            logger.info(f"Getting details {i+1}/{len(packages)}: {pkg.get('code')}")
            if pkg.get('id'):
                details = await self.get_package_details(pkg['id'])
                pkg.update(details)
            detailed_packages.append(pkg)
            await asyncio.sleep(0.5)  # Be nice to the server
        
        return detailed_packages
    
    def export_to_csv(self, packages: List[Dict[str, Any]], filename: str):
        """Export packages to CSV file"""
        if not packages:
            logger.warning("No packages to export")
            return
        
        # Get all unique keys
        all_keys = set()
        for pkg in packages:
            all_keys.update(pkg.keys())
        
        # Define column order
        priority_columns = ['id', 'code', 'program_code', 'name', 'program_name', 
                          'category', 'country', 'province', 'main_city', 
                          'expiry', 'status', 'created', 'edited']
        columns = [c for c in priority_columns if c in all_keys]
        columns.extend([k for k in sorted(all_keys) if k not in columns])
        
        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            writer.writerows(packages)
        
        logger.info(f"✅ Exported {len(packages)} packages to {filename}")
    
    def export_to_json(self, packages: List[Dict[str, Any]], filename: str):
        """Export packages to JSON file"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(packages, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ Exported {len(packages)} packages to {filename}")


async def main():
    """Main function to run the extractor"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Extract tour packages from qualityb2bpackage.com')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    parser.add_argument('--max', type=int, default=50, help='Maximum packages to extract')
    parser.add_argument('--details', action='store_true', help='Get detailed info for each package')
    parser.add_argument('--output', type=str, default='packages', help='Output filename (without extension)')
    parser.add_argument('--format', choices=['csv', 'json', 'both'], default='both', help='Output format')
    parser.add_argument('--keyword', type=str, help='Search keyword')
    args = parser.parse_args()
    
    extractor = PackageExtractor()
    
    try:
        await extractor.initialize(headless=args.headless)
        await extractor.login()
        
        filters = {}
        if args.keyword:
            filters['keyword'] = args.keyword
        
        if args.details:
            packages = await extractor.extract_all_with_details(filters, max_packages=args.max)
        else:
            packages = await extractor.extract_package_list(filters)
            packages = packages[:args.max]
        
        # Export
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_filename = f"{args.output}_{timestamp}"
        
        if args.format in ['csv', 'both']:
            extractor.export_to_csv(packages, f"{base_filename}.csv")
        
        if args.format in ['json', 'both']:
            extractor.export_to_json(packages, f"{base_filename}.json")
        
        print(f"\n📊 Extraction complete: {len(packages)} packages")
        
    finally:
        await extractor.close()


if __name__ == "__main__":
    asyncio.run(main())
