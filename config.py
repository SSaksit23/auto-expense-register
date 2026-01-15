# Configuration for Tour Charge Automation
import os
from datetime import datetime, timedelta

# Login credentials
USERNAME = "noi"
PASSWORD = "PrayuthChanocha112"

# URLs
LOGIN_URL = "https://www.qualityb2bpackage.com/"
CHARGES_FORM_URL = "https://www.qualityb2bpackage.com/charges_group/create"
TOUR_PROGRAM_LIST_URL = "https://www.qualityb2bpackage.com/travelpackage"

# CSV file path (update this to your actual path)
CSV_FILE_PATH = r"C:\Users\saksi\order-bot-automation\tour_data.csv"

# Form defaults
DESCRIPTION = "ค่าอุปกรณ์ออกทัวร์"
CHARGE_TYPE = "ค่าอุปกรณ์ออกทัวร์"
CURRENCY = "THB"

# Calculate payment date (current date + 7 days)
def get_payment_date():
    return (datetime.now() + timedelta(days=7)).strftime("%d/%m/%Y")

# Date range for tour search (wide range to cover all tours)
DATE_START = "01/01/2024"
DATE_END = "31/12/2026"

# Timeouts (in milliseconds)
DEFAULT_TIMEOUT = 30000
NAVIGATION_TIMEOUT = 60000

# Retry settings
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# Logging
LOG_FILE = "automation_log.csv"
