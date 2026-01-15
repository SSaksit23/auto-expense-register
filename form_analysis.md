# Form Structure Analysis

## Form Details
- **Form URL**: https://www.qualityb2bpackage.com/charges_group/create
- **Form Action**: https://www.qualityb2bpackage.com/charges_group/charges_save
- **Form Method**: POST
- **Form ID**: frm_submit
- **Form Name**: frm_submit

## Key Form Fields Identified

### 1. Date Range Filter (โปรแกรมช่วงวันที่)
- **Field Name**: `start` and `end`
- **Type**: Date input
- **Purpose**: Filter programs by date range
- **Default Values**: 07/01/2026 to 14/01/2026

### 2. Tour Program (โปรแกรมทัวร์)
- **Field ID**: `package`
- **Field Name**: `package`
- **Type**: Select dropdown with search
- **Purpose**: Select the tour program (Program Code)
- **Note**: Uses selectpicker with live search

### 3. Tour Code (รหัสทัวร์)
- **Field ID**: Needs to be identified from page inspection
- **Type**: Select dropdown
- **Purpose**: Select the group code
- **Note**: This dropdown is dependent on the selected program

### 4. Payment Date (วันจ่าย)
- **Type**: Date picker
- **Purpose**: Set payment date (7 days from entry date)

### 5. Description (คำอธิบาย)
- **Type**: Text input
- **Purpose**: Enter description (e.g., "ค่าเอกสารออกทัวร์")

### 6. Amount (จำนวนเงิน)
- **Type**: Number input
- **Purpose**: Enter calculated amount (50 × PAX)

### 7. Charges Number (เลขที่ค่าใช้จ่าย)
- **Field ID**: `charges_no`
- **Field Name**: `charges_no`
- **Type**: Text input with autocomplete
- **Placeholder**: C2021XX-XXXX

### 8. Company Charges (ค่าใช้จ่ายของบริษัท)
- **Field Name**: `charges[id_company_charges_agent]`
- **Type**: Select dropdown
- **Purpose**: Select company charges type

## Form Workflow

1. User selects date range filter
2. User selects tour program from dropdown (Program Code)
3. System loads corresponding group codes
4. User selects group code from dropdown
5. User enters description: "ค่าเอกสารออกทัวร์"
6. User enters amount: 50 × PAX (from Excel)
7. User sets payment date: Current date + 7 days
8. User submits form

## Additional Notes

- The form uses Bootstrap selectpicker for dropdowns
- The form has live search capability for program selection
- The form uses date pickers for date inputs
- The form may have dynamic fields that load based on selections
- The form requires authentication before access
