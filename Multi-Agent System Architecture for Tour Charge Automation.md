
# Multi-Agent System Architecture for Tour Charge Automation

## 1. Framework Recommendation: CrewAI

Both CrewAI and AutoGen are powerful frameworks for building multi-agent systems, but they have different strengths. For this project, **CrewAI is the recommended framework**. Here’s a comparison to justify this choice:

| Feature | CrewAI | AutoGen |
| :--- | :--- | :--- |
| **Core Philosophy** | Role-based, hierarchical, and sequential task execution. Well-suited for structured workflows. | Conversation-driven, flexible agent interactions. Better for complex, dynamic conversations. |
| **Agent Definition** | Agents are defined with specific roles, goals, and backstories, promoting specialization. | Agents are more general-purpose and defined by their capabilities and conversation patterns. |
| **Workflow Control** | Provides clear control over the workflow with `Process.sequential` and `Process.hierarchical` execution. | Workflow is managed through conversation patterns, which can be more complex to orchestrate for linear tasks. |
| **Ease of Use** | Generally considered easier to learn and use for structured, role-based automation tasks. | Has a steeper learning curve due to its focus on conversational flexibility. |

Given that the tour charge automation is a well-defined, sequential process, CrewAI’s role-based and process-oriented approach is a natural fit. It will allow us to create a clear, maintainable, and robust multi-agent system where each agent has a distinct responsibility.

## 2. Multi-Agent Architecture with CrewAI

The proposed architecture consists of a crew of five specialized agents, each responsible for a specific part of the automation process. The agents will work in a sequential workflow, passing the necessary information to the next agent in the chain.

### 2.1. Agent Roles and Responsibilities

Here are the definitions for each agent in the crew:

| Agent | Role | Goal | Backstory |
| :--- | :--- | :--- | :--- |
| **Program Search Agent** | Tour Program Specialist | Find the correct program code for a given tour code. | An expert in the QualityB2BPackage system, with a deep understanding of how tour codes and program codes are related. |
| **Data Preparation Agent** | Data Entry Specialist | Prepare all necessary data for the expense form. | A meticulous data analyst who ensures all data is accurate and correctly formatted before it is entered into any system. |
| **Form Access Agent** | Web Navigation Expert | Log in to the system and navigate to the expense order form. | A skilled web navigator who can efficiently bypass login screens and find the correct page for any task. |
| **Form Submission Agent** | Automation Scripter | Fill and submit the expense order form with the provided data. | A proficient automation engineer who specializes in interacting with web forms, especially complex ones with dynamic elements. |
| **Result Retrieval Agent** | Data Extraction Specialist | Retrieve the expense order number after the form is submitted. | A detail-oriented data extractor who can find and parse specific information from a web page after an action has been completed. |

### 2.2. Task Definitions

Each agent will be assigned a specific task that aligns with its role:

| Task | Agent | Description | Expected Output |
| :--- | :--- | :--- | :--- |
| **Find Program Code** | Program Search Agent | Given a tour code, search the QualityB2BPackage system to find the corresponding program code. | The program code as a string. |
| **Prepare Form Data** | Data Preparation Agent | Take the program code, tour code, and PAX number to prepare a dictionary of all data needed for the form. | A JSON object containing all the data for the form fields. |
| **Access Expense Form** | Form Access Agent | Log in to the system and navigate to the expense order creation page. | The URL of the expense order form. |
| **Submit Expense Form** | Form Submission Agent | Using the data from the previous agent, fill out and submit the expense form. | A success message indicating the form was submitted. |
| **Retrieve Order Number** | Result Retrieval Agent | After the form is submitted, find and extract the newly created expense order number from the page. | The expense order number as a string. |

### 2.3. Workflow

The crew will operate in a **sequential process**, ensuring that each step is completed successfully before the next one begins. The workflow will be as follows:

1.  The **Program Search Agent** receives a tour code and finds the program code.
2.  The output (program code) is passed to the **Data Preparation Agent**, which creates the complete data payload.
3.  The **Form Access Agent** logs in and navigates to the form page.
4.  The **Form Submission Agent** takes the data payload and fills out and submits the form.
5.  Finally, the **Result Retrieval Agent** extracts the expense order number from the confirmation page.

This modular, agent-based approach will make the automation more resilient, easier to debug, and simpler to extend in the future. Each agent can be developed and tested independently, and the clear separation of concerns will lead to a more maintainable codebase.
