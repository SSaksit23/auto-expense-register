# Development Plan: n8n Workflow for Tour Charge Automation

## 1. Introduction

This document provides a detailed development plan for creating an n8n workflow to automate the tour charge creation process on the QualityB2BPackage website. The plan outlines the complete workflow structure, node configurations, and the necessary code for implementation. This automation will significantly improve efficiency and reduce manual data entry errors by reading tour charge information from an Excel file and programmatically submitting it through the web form.

## 2. n8n Workflow Overview

The n8n workflow will be designed to be robust and user-friendly, with clear steps for data processing and web automation. The workflow will consist of the following nodes, each configured to perform a specific part of the automation task.

| Node | Type | Purpose |
| :--- | :--- | :--- |
| 1 | **Start** | Manually trigger the workflow. |
| 2 | **Read From File** | Read the input Excel file containing tour charge data. |
| 3 | **Split in Batches** | Process each row from the Excel file as an individual item. |
| 4 | **Set** | Prepare and format the data for form submission. |
| 5 | **Browser Automation (Puppeteer)** | Perform the core web automation tasks, including form filling and submission. |
| 6 | **If** | Implement error handling to manage failed submissions. |
| 7 | **NoOp** | Serve as a placeholder for successful and failed branches. |

## 3. Node Configuration and Implementation Details

This section provides detailed configuration for each node in the n8n workflow, including the necessary expressions and code snippets.

### 3.1. Read From File Node

This node will be configured to read the Excel file provided by the user. The file should be placed in a location accessible to the n8n instance.

- **File Path**: Specify the full path to the input Excel file (e.g., `/data/tour_charges.xlsx`).
- **Sheet Name**: Enter the name of the sheet containing the data.

### 3.2. Split in Batches Node

This node will split the data from the Excel file into individual items, allowing the workflow to process one tour charge at a time.

- **Batch Size**: `1`

### 3.3. Set Node

This node will prepare the data for the form. It will calculate the `amount` and `payment_date` based on the input from the Excel file.

| Name | Value |
| :--- | :--- |
| `amount` | `{{ $json.total_pax * 50 }}` |
| `payment_date` | `{{ new Date(new Date().setDate(new Date().getDate() + 7)).toLocaleDateString("en-GB") }}` |

### 3.4. Browser Automation (Puppeteer) Node

This is the core node of the workflow. It will use Puppeteer to interact with the website and submit the form. The following steps will be configured within this node:

1.  **Navigate to the form page**:
    *   **Action**: Go to
    *   **URL**: `https://www.qualityb2bpackage.com/charges_group/create`

2.  **Select the Tour Program**:
    *   **Action**: Click
    *   **Selector**: `button[data-id='package']`
    *   **Action**: Type
    *   **Selector**: `div.bs-searchbox > input`
    *   **Text**: `{{ $json.program_code }}`
    *   **Action**: Click
    *   **Selector**: `ul.dropdown-menu.inner > li > a > span.text` (This will need to be made more specific to select the correct program)

3.  **Select the Tour Code**:
    *   **Action**: Wait for
    *   **Selector**: `button[data-id='group_code_package']` (This selector needs to be verified)
    *   **Action**: Click
    *   **Selector**: `button[data-id='group_code_package']`
    *   **Action**: Type
    *   **Selector**: `div.bs-searchbox > input`
    *   **Text**: `{{ $json.group_code }}`
    *   **Action**: Click
    *   **Selector**: `ul.dropdown-menu.inner > li > a > span.text`

4.  **Fill in the form fields**:
    *   **Action**: Type
    *   **Selector**: `input[name='charges_d[description][]']` (This selector needs to be verified as it is a dynamic field)
    *   **Text**: `ค่าเอกสารออกทัวร์`
    *   **Action**: Type
    *   **Selector**: `input[name='charges_d[amount][]']` (This selector needs to be verified as it is a dynamic field)
    *   **Text**: `{{ $json.amount }}`
    *   **Action**: Type
    *   **Selector**: `input[name='date_pay']`
    *   **Text**: `{{ $json.payment_date }}`

5.  **Submit the form**:
    *   **Action**: Click
    *   **Selector**: `input[type='submit'][value='Save']`

### 3.5. Error Handling

The **If** node will be used to check if the form submission was successful. This can be done by checking for a success message on the page or by checking the URL after submission. If the submission fails, the workflow can be configured to log the error to a file or send a notification.

## 4. Conclusion

This development plan provides a comprehensive guide for creating an n8n workflow to automate the tour charge creation process. By following these steps, you can build a robust and efficient automation that will save time and reduce errors. The plan includes all the necessary details for implementation, but it is important to note that some of the CSS selectors for dynamic fields will need to be verified during the development process by inspecting the live website.
