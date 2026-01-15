"""
CrewAI Task Definitions for Tour Charge Automation
Each task defines what an agent needs to accomplish.
"""

from crewai import Task
from datetime import datetime, timedelta
from typing import Optional


def create_login_task(agent) -> Task:
    """
    Create the login task for authenticating with the system.
    """
    return Task(
        description="""Log in to the QualityB2BPackage system at https://www.qualityb2bpackage.com/
        
        Steps:
        1. Navigate to the login page
        2. Enter the credentials (from environment variables)
        3. Click the login button
        4. Verify successful authentication
        
        Report success or any issues encountered.""",
        expected_output="Confirmation that login was successful or details of any login failure.",
        agent=agent
    )


def create_find_program_code_task(agent, tour_code: str) -> Task:
    """
    Create the task for finding the program code.
    """
    return Task(
        description=f"""Find the program code for tour code: {tour_code}
        
        The tour code follows this structure:
        - {tour_code[:5]} is the base program identifier
        - The last 2 letters before the 6-digit date are the airline code (e.g., CZ, FD)
        
        Search the QualityB2BPackage system to find or derive the correct program code.
        Program codes typically look like: {tour_code[:5]}-XX001 where XX is the airline code.
        
        Return the program code in the format: XXXXX-XXNNN (e.g., G8HRB-CZ001)""",
        expected_output=f"The program code as a string (e.g., {tour_code[:5]}-XX001)",
        agent=agent
    )


def create_prepare_form_data_task(agent, tour_code: str, pax: int, amount: float) -> Task:
    """
    Create the task for preparing form data.
    """
    payment_date = (datetime.now() + timedelta(days=7)).strftime("%d/%m/%Y")
    
    return Task(
        description=f"""Prepare all data needed for the expense form:
        
        Input Data:
        - Tour Code: {tour_code}
        - PAX (Passengers): {pax}
        - Amount: {amount} THB
        - Payment Date: {payment_date} (7 days from today)
        
        Prepare the following fields:
        1. Date Range: 01/01/2024 to 31/12/2026
        2. Program Code: (from previous task)
        3. Tour Code: {tour_code}
        4. Payment Date: {payment_date}
        5. Description: ค่าอุปกรณ์ออกทัวร์
        6. Charge Type: ค่าใช้จ่ายเบ็ดเตล็ด
        7. Amount: {amount} THB
        
        Also prepare the remark template:
        - เลขที่: (to be filled after submission)
        - Program: [Program Code]
        - Code Program: [Program Code]
        - Code group: {tour_code}
        - รายละเอียด: ค่าอุปกรณ์ออกทัวร์ 50 (Fixed) x {pax} PAX = {int(amount)} THB
        - ยอดเงินรวม: {int(amount)} THB
        - วันจ่าย: {payment_date}
        
        And company expense data:
        - Company: GO365 TRAVEL CO.,LTD.
        - Payment Method: โอนเข้าบัญชี
        - Payment Type: เบ็ดเตล็ด
        - Period: {tour_code}""",
        expected_output="Confirmation that all form data has been prepared and validated.",
        agent=agent
    )


def create_navigate_to_form_task(agent) -> Task:
    """
    Create the task for navigating to the charges form.
    """
    return Task(
        description="""Navigate to the charges group creation form.
        
        Steps:
        1. Go to https://www.qualityb2bpackage.com/charges_group/create
        2. Wait for the page to fully load
        3. Verify the form is visible and ready for input
        
        Report the current URL and page status.""",
        expected_output="Confirmation that navigation to the charges form was successful.",
        agent=agent
    )


def create_fill_form_task(agent, tour_code: str, pax: int, amount: float) -> Task:
    """
    Create the task for filling and submitting the form.
    """
    return Task(
        description=f"""Fill out and submit the expense form with the following data:
        
        Tour Code: {tour_code}
        PAX: {pax}
        Amount: {amount} THB
        
        Follow these steps:
        1. Set date range: 01/01/2024 to 31/12/2026
        2. Select the program code from the dropdown (from previous task result)
        3. Select the tour code: {tour_code}
        4. Fill payment date (7 days from today)
        5. Fill description: ค่าอุปกรณ์ออกทัวร์
        6. Select type: ค่าใช้จ่ายเบ็ดเตล็ด (เบ็ดเตล็ด)
        7. Fill amount: {amount}
        8. Fill the remark with the template
        9. Enable company expense section
        10. Select company: GO365 TRAVEL CO.,LTD.
        11. Select payment method: โอนเข้าบัญชี
        12. Fill company amount: {amount}
        13. Select payment type: เบ็ดเตล็ด
        14. Fill payment date
        15. Fill period: {tour_code}
        16. Fill company remark
        17. Click Save to submit
        
        Wait for the form to be submitted successfully.""",
        expected_output="Confirmation that the form was filled and submitted successfully.",
        agent=agent
    )


def create_retrieve_expense_number_task(agent, tour_code: str) -> Task:
    """
    Create the task for retrieving the expense number.
    """
    return Task(
        description=f"""After the form for tour code {tour_code} has been submitted, 
        extract the expense order number from the page.
        
        The expense number format is: CYYMMDD-XXXXXX (e.g., C202614-139454)
        
        Look for the number in:
        1. Input fields on the page
        2. Success message or confirmation
        3. Page text content
        4. URL parameters
        
        Return the expense number or report if it couldn't be found.""",
        expected_output="The expense order number in format CYYMMDD-XXXXXX, or a note that it wasn't found.",
        agent=agent
    )


def create_all_tasks_for_entry(agents: dict, tour_code: str, pax: int, amount: float) -> list:
    """
    Create all tasks for processing a single tour entry.
    
    Args:
        agents: Dictionary of agent instances
        tour_code: The tour code to process
        pax: Number of passengers
        amount: Expense amount
    
    Returns:
        List of Task objects in execution order
    """
    tasks = [
        create_login_task(agents['login']),
        create_find_program_code_task(agents['program_search'], tour_code),
        create_navigate_to_form_task(agents['form_access']),
        create_fill_form_task(agents['form_submission'], tour_code, pax, amount),
        create_retrieve_expense_number_task(agents['result_retrieval'], tour_code)
    ]
    
    return tasks
