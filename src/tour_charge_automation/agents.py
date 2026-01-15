"""
CrewAI Agent Definitions for Tour Charge Automation
Each agent has a specific role, goal, and backstory to guide its behavior.
"""

import os
from crewai import Agent, LLM
from dotenv import load_dotenv
from .tools.browser_tools import (
    LoginTool, 
    FindProgramCodeTool, 
    NavigateToFormTool, 
    FillFormTool, 
    ExtractExpenseNumberTool
)

# Load environment variables
load_dotenv()

def get_llm():
    """Get configured LLM instance for agents."""
    model_name = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")
    api_key = os.getenv("OPENAI_API_KEY")
    
    return LLM(
        model=f"openai/{model_name}",
        api_key=api_key
    )


def create_login_agent() -> Agent:
    """
    Create the Login Agent responsible for authenticating with the system.
    """
    return Agent(
        role="Authentication Specialist",
        goal="Successfully log in to the QualityB2BPackage system and establish a session.",
        backstory="""You are a security-conscious authentication specialist who ensures 
        secure access to the QualityB2BPackage system. You handle login credentials 
        carefully and verify successful authentication before proceeding.""",
        tools=[LoginTool()],
        llm=get_llm(),
        verbose=True,
        allow_delegation=False,
        max_iter=3
    )


def create_program_search_agent() -> Agent:
    """
    Create the Program Search Agent responsible for finding program codes.
    """
    return Agent(
        role="Tour Program Specialist",
        goal="Find the correct program code for a given tour code in the QualityB2BPackage system.",
        backstory="""You are an expert in the QualityB2BPackage system with deep knowledge 
        of how tour codes and program codes are structured. You understand the naming 
        conventions: tour codes like 'G8HRB5NHRBCZ250103' map to program codes like 
        'G8HRB-CZ001'. The first 5 characters are the base, followed by the airline 
        code (e.g., CZ, FD) and a sequence number.""",
        tools=[FindProgramCodeTool()],
        llm=get_llm(),
        verbose=True,
        allow_delegation=False,
        max_iter=5
    )


def create_data_preparation_agent() -> Agent:
    """
    Create the Data Preparation Agent responsible for preparing form data.
    """
    return Agent(
        role="Data Entry Specialist",
        goal="Prepare all necessary data for the expense form with correct formatting and calculations.",
        backstory="""You are a meticulous data analyst who ensures all data is accurate 
        and correctly formatted. You understand Thai date formats (DD/MM/YYYY), can 
        calculate payment dates (7 days from today), and know how to structure the 
        remark templates required for tour expense documentation. You never make 
        calculation errors and always double-check your work.""",
        tools=[],  # This agent uses reasoning, not tools
        llm=get_llm(),
        verbose=True,
        allow_delegation=False,
        max_iter=3
    )


def create_form_access_agent() -> Agent:
    """
    Create the Form Access Agent responsible for navigating to the form.
    """
    return Agent(
        role="Web Navigation Expert",
        goal="Navigate to the expense order form page after authentication.",
        backstory="""You are a skilled web navigator who can efficiently find the 
        correct pages in complex web applications. You know the QualityB2BPackage 
        system structure and can quickly locate the charges group creation page 
        at /charges_group/create.""",
        tools=[NavigateToFormTool()],
        llm=get_llm(),
        verbose=True,
        allow_delegation=False,
        max_iter=3
    )


def create_form_submission_agent() -> Agent:
    """
    Create the Form Submission Agent responsible for filling and submitting the form.
    """
    return Agent(
        role="Automation Scripter",
        goal="Fill out and submit the expense order form with complete accuracy.",
        backstory="""You are a proficient automation engineer who specializes in 
        interacting with complex web forms, especially those with dynamic elements 
        like Bootstrap selectpicker dropdowns. You understand that the QualityB2BPackage 
        form requires:
        1. Setting date range (01/01/2024 to 31/12/2026)
        2. Selecting the program from a dropdown
        3. Selecting the tour code from a dependent dropdown
        4. Filling payment date, description, type, and amount
        5. Adding company expense with GO365 TRAVEL CO.,LTD.
        6. Using 'โอนเข้าบัญชี' for payment method
        7. Using 'เบ็ดเตล็ด' for payment type
        You are patient with slow-loading elements and retry when needed.""",
        tools=[FillFormTool()],
        llm=get_llm(),
        verbose=True,
        allow_delegation=False,
        max_iter=5
    )


def create_result_retrieval_agent() -> Agent:
    """
    Create the Result Retrieval Agent responsible for extracting the expense number.
    """
    return Agent(
        role="Data Extraction Specialist",
        goal="Retrieve the expense order number after form submission.",
        backstory="""You are a detail-oriented data extractor who can find and parse 
        specific information from web pages. You know that expense numbers in the 
        QualityB2BPackage system follow the format 'C202614-139454' (CYYMMDD-XXXXXX). 
        You check multiple locations: input fields, page text, success messages, 
        and URL parameters to find this number.""",
        tools=[ExtractExpenseNumberTool()],
        llm=get_llm(),
        verbose=True,
        allow_delegation=False,
        max_iter=3
    )


def create_all_agents() -> dict:
    """
    Create all agents and return them as a dictionary.
    """
    return {
        'login': create_login_agent(),
        'program_search': create_program_search_agent(),
        'data_preparation': create_data_preparation_agent(),
        'form_access': create_form_access_agent(),
        'form_submission': create_form_submission_agent(),
        'result_retrieval': create_result_retrieval_agent()
    }
