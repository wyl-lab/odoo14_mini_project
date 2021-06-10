# -*- coding: utf-8 -*-
# 报表设计
documentProperties = {  # 文档参数-固定
    "pageFormat": "A4",
    "pageWidth": "",
    "pageHeight": "",
    "unit": "mm",
    "orientation": "portrait",
    "contentHeight": "",
    "marginLeft": "20",
    "marginTop": "20",
    "marginRight": "20",
    "marginBottom": "10",
    "header": True,
    "headerSize": "60",
    "headerDisplay": "always",
    "footer": True,
    "footerSize": "60",
    "footerDisplay": "always",
    "patternLocale": "de",
    "patternCurrencySymbol": "￥"
}
docElements = []  # 报表元素位置
styles = []  # 样式
parameters = [  # 报表数据
    {
        "id": 10,
        "name": "页数",
        "type": "number",
        "eval": False,
        "pattern": "",
        "expression": "",
        "showOnlyNameType": True,
        "testData": ""
    },
    {
        "id": 11,
        "name": "页码",
        "type": "number",
        "eval": False,
        "pattern": "",
        "expression": "",
        "showOnlyNameType": True,
        "testData": ""
    },
    {
        "id": 12,
        "name": "Invoice",
        "type": "array",
        "eval": False,
        "pattern": "",
        "expression": "",
        "showOnlyNameType": False,
        "testData": "[{\"Description\":\"Website Requirements Definition\",\"VAT\":\"20\",\"UnitPrice\":\"120\",\"Quantity\":\"14,25\",\"Amount\":\"1710\"},{\"Description\":\"Web Design\",\"VAT\":\"20\",\"UnitPrice\":\"120\",\"Quantity\":\"28\",\"Amount\":\"3360\"},{\"Description\":\"Web Development\",\"VAT\":\"20\",\"UnitPrice\":\"135\",\"Quantity\":\"57\",\"Amount\":\"7695\"},{\"Description\":\"QA & Testing\",\"VAT\":\"20\",\"UnitPrice\":\"100\",\"Quantity\":\"12\",\"Amount\":\"1200\"},{\"Description\":\"Deployment & Server Maintenance\",\"VAT\":\"20\",\"UnitPrice\":\"110\",\"Quantity\":\"8\",\"Amount\":\"880\"}]",
        "children": [
            {
                "id": 13,
                "name": "Description",
                "type": "string",
                "eval": False,
                "pattern": "",
                "expression": "",
                "showOnlyNameType": False,
                "testData": ""
            },
            {
                "id": 14,
                "name": "VAT",
                "type": "number",
                "eval": False,
                "pattern": "#,##0",
                "expression": "",
                "showOnlyNameType": False,
                "testData": ""
            },
            {
                "id": 15,
                "name": "UnitPrice",
                "type": "number",
                "eval": False,
                "pattern": "#,##0.00",
                "expression": "",
                "showOnlyNameType": False,
                "testData": ""
            },
            {
                "id": 16,
                "name": "Quantity",
                "type": "number",
                "eval": False,
                "pattern": "#,##0.00",
                "expression": "",
                "showOnlyNameType": False,
                "testData": ""
            },
            {
                "id": 17,
                "name": "Amount",
                "type": "number",
                "eval": False,
                "pattern": "#,##0.00",
                "expression": "",
                "showOnlyNameType": False,
                "testData": ""
            }
        ]
    },
    {
        "id": 18,
        "name": "Recipient",
        "type": "map",
        "eval": False,
        "pattern": "",
        "expression": "",
        "showOnlyNameType": False,
        "testData": "",
        "children": [
            {
                "id": 19,
                "name": "Company",
                "type": "string",
                "eval": False,
                "pattern": "",
                "expression": "",
                "showOnlyNameType": False,
                "testData": "Mayer Consulting"
            },
            {
                "id": 20,
                "name": "LastName",
                "type": "string",
                "eval": False,
                "pattern": "",
                "expression": "",
                "showOnlyNameType": False,
                "testData": "Mayer"
            },
            {
                "id": 21,
                "name": "FirstName",
                "type": "string",
                "eval": False,
                "pattern": "",
                "expression": "",
                "showOnlyNameType": False,
                "testData": "Max"
            },
            {
                "id": 22,
                "name": "AddressStreet",
                "type": "string",
                "eval": False,
                "pattern": "",
                "expression": "",
                "showOnlyNameType": False,
                "testData": "Freihausgasse 17"
            },
            {
                "id": 23,
                "name": "ZIP",
                "type": "string",
                "eval": False,
                "pattern": "",
                "expression": "",
                "showOnlyNameType": False,
                "testData": "1040"
            },
            {
                "id": 24,
                "name": "City",
                "type": "string",
                "eval": False,
                "pattern": "",
                "expression": "",
                "showOnlyNameType": False,
                "testData": "Wien"
            }
        ]
    },
    {
        "id": 25,
        "name": "InvoiceDetails",
        "type": "map",
        "eval": False,
        "pattern": "",
        "expression": "",
        "showOnlyNameType": False,
        "testData": "",
        "children": [
            {
                "id": 26,
                "name": "InvoiceAmountNet",
                "type": "sum",
                "eval": False,
                "pattern": "#,##0.00",
                "expression": "${Invoice.Amount}",
                "showOnlyNameType": False,
                "testData": ""
            },
            {
                "id": 27,
                "name": "InvoiceTax",
                "type": "number",
                "eval": True,
                "pattern": "#,##0.00",
                "expression": "${InvoiceDetails.InvoiceAmountNet}/100*20",
                "showOnlyNameType": False,
                "testData": ""
            },
            {
                "id": 28,
                "name": "InvoiceAmountGross",
                "type": "number",
                "eval": True,
                "pattern": "#,##0.00",
                "expression": "${InvoiceDetails.InvoiceAmountNet}+${InvoiceDetails.InvoiceTax}",
                "showOnlyNameType": False,
                "testData": ""
            },
            {
                "id": 29,
                "name": "InvoiceNumber",
                "type": "number",
                "eval": False,
                "pattern": "",
                "expression": "",
                "showOnlyNameType": False,
                "testData": "123"
            },
            {
                "id": 30,
                "name": "InvoiceDate",
                "type": "date",
                "eval": False,
                "pattern": "d. MMMM yyyy",
                "expression": "",
                "showOnlyNameType": False,
                "testData": "2017-06-12"
            }
        ]
    },
    {
        "id": 31,
        "name": "CompanyDetails",
        "type": "map",
        "eval": False,
        "pattern": "",
        "expression": "",
        "showOnlyNameType": False,
        "testData": "",
        "children": [
            {
                "id": 32,
                "name": "Name",
                "type": "string",
                "eval": False,
                "pattern": "",
                "expression": "",
                "showOnlyNameType": False,
                "testData": "MyCompany, Inc."
            },
            {
                "id": 33,
                "name": "Street",
                "type": "string",
                "eval": False,
                "pattern": "",
                "expression": "",
                "showOnlyNameType": False,
                "testData": "Invented Street 843"
            },
            {
                "id": 34,
                "name": "City",
                "type": "string",
                "eval": False,
                "pattern": "",
                "expression": "",
                "showOnlyNameType": False,
                "testData": "12345 Company City"
            },
            {
                "id": 35,
                "name": "WebAddress",
                "type": "string",
                "eval": False,
                "pattern": "",
                "expression": "",
                "showOnlyNameType": False,
                "testData": "www.reportbro.com"
            },
            {
                "id": 36,
                "name": "IBAN",
                "type": "string",
                "eval": False,
                "pattern": "",
                "expression": "",
                "showOnlyNameType": False,
                "testData": "AT25 1420 0123 1234 1234"
            },
            {
                "id": 37,
                "name": "Bank",
                "type": "string",
                "eval": False,
                "pattern": "",
                "expression": "",
                "showOnlyNameType": False,
                "testData": "easybank"
            },
            {
                "id": 38,
                "name": "BIC",
                "type": "string",
                "eval": False,
                "pattern": "",
                "expression": "",
                "showOnlyNameType": False,
                "testData": "EASYATW1"
            },
            {
                "id": 39,
                "name": "UID",
                "type": "string",
                "eval": False,
                "pattern": "",
                "expression": "",
                "showOnlyNameType": False,
                "testData": "ATU12345678"
            }
        ]
    }
]
