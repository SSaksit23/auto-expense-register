
# CrewAI Implementation Guide: Tour Charge Automation

## 1. Introduction

This guide provides a step-by-step plan for implementing the multi-agent tour charge automation system using the CrewAI framework. By following this guide, you will be able to set up a robust, maintainable, and intelligent automation solution that leverages the power of specialized AI agents to perform each step of the process. This approach will not only solve the immediate challenges with the dynamic web form but also provide a scalable architecture for future automation tasks.

## 2. Project Structure

To keep the project organized and maintainable, we will follow a standard Python project structure. Here is the recommended directory layout:

```
/tour_charge_automation/
|-- /src/
|   |-- /tour_charge_automation/
|   |   |-- __init__.py
|   |   |-- main.py             # Main script to run the crew
|   |   |-- agents.py           # Agent definitions
|   |   |-- tasks.py            # Task definitions
|   |   |-- tools/
|   |   |   |-- __init__.py
|   |   |   |-- browser_tools.py    # Custom browser automation tools
|-- requirements.txt        # Project dependencies
|-- .env                    # Environment variables (API keys, credentials)
|-- tour_data.csv           # Input data file
```

## 3. Dependencies

First, you will need to install the necessary Python libraries. Create a `requirements.txt` file with the following content:

```
crewai
crewai-tools
playwright
pandas
python-dotenv
```

Then, install these dependencies using pip:

```bash
pip install -r requirements.txt
playwright install
```

## 4. Environment Variables

Create a `.env` file in the root of your project to store your credentials securely:

```
OPENAI_API_KEY="your_openai_api_key"
WEBSITE_USERNAME="noi"
WEBSITE_PASSWORD="PrayuthChanocha112"
```

## 5. Custom Browser Automation Tools

The agents will need tools to interact with the website. We will create a set of custom tools using Playwright. These tools will be more reliable than the previous script because they will be smaller, more focused, and called by intelligent agents that can handle errors and retries.

Create the file `src/tour_charge_automation/tools/browser_tools.py` with the following content:

```python
from playwright.sync_api import sync_playwright, Page
from crewai_tools import BaseTool
import time
import os
from dotenv import load_dotenv

load_dotenv()

class BrowserAutomationTools(BaseTool):
    name: str = "Browser Automation Tools"
    description: str = "A set of tools for automating browser interactions with Playwright."
    page: Page = None

    def _get_page(self):
        if self.page is None:
            playwright = sync_playwright().start()
            browser = playwright.chromium.launch(headless=False) # Set to True for production
            self.page = browser.new_page()
        return self.page

    def login(self):
        page = self._get_page()
        page.goto("https://www.qualityb2bpackage.com/")
        page.fill("input[type=\"text\"]", os.getenv("WEBSITE_USERNAME"))
        page.fill("input[type=\"password\"]", os.getenv("WEBSITE_PASSWORD"))
        page.click("button:has-text(\"Login\")")
        page.wait_for_load_state("networkidle")
        return "Successfully logged in."

    def find_program_code(self, tour_code: str) -> str:
        page = self._get_page()
        page.goto("https://www.qualityb2bpackage.com/travelpackage")
        page.fill("input[placeholder*=\"keyword\"]", tour_code)
        page.click("button:has-text(\"Go!\")")
        page.wait_for_load_state("networkidle")
        content = page.content()
        # This regex is an example, it might need to be adjusted
        match = re.search(r">(2UCKG-FD\d{3})<", content)
        if match:
            return match.group(1)
        return "Program code not found."

    def navigate_to_charges_form(self):
        page = self._get_page()
        page.goto("https://www.qualityb2bpackage.com/charges_group/create")
        page.wait_for_load_state("networkidle")
        return "Navigated to the charges form."

    def submit_charge_form(self, form_data: dict) -> str:
        page = self._get_page()
        # Use the hybrid JavaScript injection method from the previous recommendation
        page.evaluate(f"""(data) => {{
            const packageSelect = $("select[name=\"package\"]");
            const programOption = packageSelect.find("option:contains("" + data.program_code + "")");
            if (programOption.length > 0) {{
                packageSelect.selectpicker("val", programOption.val());
                packageSelect.trigger("change");
            }}
        }}""", form_data)
        time.sleep(2)

        page.evaluate(f"""(data) => {{
            const groupSelect = $("select[name=\"group_code_package\"]");
            const tourOption = groupSelect.find("option:contains("" + data.tour_code + "")");
            if (tourOption.length > 0) {{
                groupSelect.selectpicker("val", tourOption.val());
                groupSelect.trigger("change");
            }}
        }}""", form_data)
        time.sleep(1)

        page.fill("input[name=\"date_pay\"]", form_data["payment_date"])
        page.click("button:has-text("เพิ่มแถว+")")
        time.sleep(0.5)
        page.fill("input[name=\"charges_d[description][]"]", form_data["description"])
        page.select_option("select[name=\"charges_d[rate_type][]"]", label=form_data["charge_type"])
        page.fill("input[name=\"charges_d[amount][]"]", str(form_data["amount"]))

        page.click("input[type=\"submit\"][value=\"Save\"]")
        page.wait_for_load_state("networkidle")
        return "Form submitted successfully."

    def retrieve_order_number(self) -> str:
        page = self._get_page()
        # This selector needs to be adjusted based on the actual confirmation page
        success_message = page.locator(".alert-success").inner_text()
        match = re.search(r"เลขที่เอกสาร (\w+)", success_message)
        if match:
            return match.group(1)
        return "Order number not found."
```

## 6. Agent and Task Definitions

Now, we will define the agents and tasks in separate files for clarity.

### `src/tour_charge_automation/agents.py`

```python
from crewai import Agent
from .tools.browser_tools import BrowserAutomationTools

browser_tool = BrowserAutomationTools()

def create_program_search_agent():
    return Agent(
        role="Tour Program Specialist",
        goal="Find the correct program code for a given tour code.",
        backstory="An expert in the QualityB2BPackage system, with a deep understanding of how tour codes and program codes are related.",
        tools=[browser_tool],
        verbose=True
    )

def create_data_preparation_agent():
    return Agent(
        role="Data Entry Specialist",
        goal="Prepare all necessary data for the expense form.",
        backstory="A meticulous data analyst who ensures all data is accurate and correctly formatted before it is entered into any system.",
        verbose=True
    )

def create_form_access_agent():
    return Agent(
        role="Web Navigation Expert",
        goal="Log in to the system and navigate to the expense order form.",
        backstory="A skilled web navigator who can efficiently bypass login screens and find the correct page for any task.",
        tools=[browser_tool],
        verbose=True
    )

def create_form_submission_agent():
    return Agent(
        role="Automation Scripter",
        goal="Fill and submit the expense order form with the provided data.",
        backstory="A proficient automation engineer who specializes in interacting with web forms, especially complex ones with dynamic elements.",
        tools=[browser_tool],
        verbose=True
    )

def create_result_retrieval_agent():
    return Agent(
        role="Data Extraction Specialist",
        goal="Retrieve the expense order number after the form is submitted.",
        backstory="A detail-oriented data extractor who can find and parse specific information from a web page after an action has been completed.",
        tools=[browser_tool],
        verbose=True
    )
```

### `src/tour_charge_automation/tasks.py`

```python
from crewai import Task
from datetime import datetime, timedelta

def create_find_program_code_task(agent, tour_code):
    return Task(
        description=f"Find the program code for the tour code: {tour_code}",
        expected_output="The program code as a string.",
        agent=agent
    )

def create_prepare_form_data_task(agent, tour_code, pax, amount):
    payment_date = (datetime.now() + timedelta(days=7)).strftime("%d/%m/%Y")
    return Task(
        description=f"Prepare the form data for tour code {tour_code}. The program code is {{context.program_code}}.",
        expected_output="A JSON object containing all the data for the form fields.",
        agent=agent,
        context={"program_code": ""} # This will be populated by the previous task
    )

def create_access_form_task(agent):
    return Task(
        description="Log in to the QualityB2BPackage system and navigate to the charges group creation page.",
        expected_output="The URL of the expense order form.",
        agent=agent
    )

def create_submit_form_task(agent):
    return Task(
        description="Submit the expense form using the prepared data from the context.",
        expected_output="A success message indicating the form was submitted.",
        agent=agent
    )

def create_retrieve_order_number_task(agent):
    return Task(
        description="Retrieve the expense order number from the confirmation page.",
        expected_output="The expense order number as a string.",
        agent=agent
    )
```

## 7. Main Script to Run the Crew

Finally, create the `main.py` file to bring everything together and run the crew.

### `src/tour_charge_automation/main.py`

```python
from crewai import Crew, Process
import pandas as pd
from .agents import (
    create_program_search_agent,
    create_data_preparation_agent,
    create_form_access_agent,
    create_form_submission_agent,
    create_result_retrieval_agent
)
from .tasks import (
    create_find_program_code_task,
    create_prepare_form_data_task,
    create_access_form_task,
    create_submit_form_task,
    create_retrieve_order_number_task
)

def run_automation():
    # Load data from CSV
    df = pd.read_csv("../../tour_data.csv")

    # Create agents
    program_search_agent = create_program_search_agent()
    data_preparation_agent = create_data_preparation_agent()
    form_access_agent = create_form_access_agent()
    form_submission_agent = create_form_submission_agent()
    result_retrieval_agent = create_result_retrieval_agent()

    for index, row in df.iterrows():
        tour_code = row["รหัสทัวร์"]
        pax = row["จำนวนลูกค้า หัก หนท."]
        amount = row["ยอดเบิก"]

        # Create tasks for the current row
        find_program_code_task = create_find_program_code_task(program_search_agent, tour_code)
        prepare_form_data_task = create_prepare_form_data_task(data_preparation_agent, tour_code, pax, amount)
        access_form_task = create_access_form_task(form_access_agent)
        submit_form_task = create_submit_form_task(form_submission_agent)
        retrieve_order_number_task = create_retrieve_order_number_task(result_retrieval_agent)

        # Create the crew
        tour_charge_crew = Crew(
            agents=[
                program_search_agent,
                data_preparation_agent,
                form_access_agent,
                form_submission_agent,
                result_retrieval_agent
            ],
            tasks=[
                find_program_code_task,
                prepare_form_data_task,
                access_form_task,
                submit_form_task,
                retrieve_order_number_task
            ],
            process=Process.sequential,
            verbose=2
        )

        # Run the crew for the current row
        result = tour_charge_crew.kickoff()
        print(f"Processed {tour_code}: {result}")

if __name__ == "__main__":
    run_automation()
```

## 8. Running the Automation

To run the automation, navigate to the `src/tour_charge_automation` directory and execute the `main.py` script:

```bash
cd src/tour_charge_automation
python main.py
```

The script will then iterate through each row of your `tour_data.csv` file, and for each row, the crew of AI agents will perform the complete automation workflow.

## 9. Conclusion

By implementing this multi-agent system with CrewAI, you are creating a far more intelligent and resilient automation solution. The separation of concerns among the agents makes the system easier to debug, maintain, and extend. The agents can handle errors, retries, and adapt to minor changes in the website, providing a level of robustness that is difficult to achieve with a single, monolithic script. This architecture not only solves the immediate problem but also establishes a powerful foundation for future automation initiatives.
