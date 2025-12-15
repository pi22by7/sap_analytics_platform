# Data Dictionary

## Overview
The SAP Procurement Analytics Platform uses a standard SAP-like schema with 6 core tables. This document details the structure and fields of each table.

## LFA1 - Vendor Master
Contains vendor master data including address and control fields.

| Field | Description | Type | Example |
|-------|-------------|------|---------|
| `LIFNR` | Vendor Account Number (PK) | String (10) | V0000001 |
| `NAME1` | Name | String | Acme Corp |
| `LAND1` | Country Key | String (2) | US |
| `ORT01` | City | String | New York |
| `KTOKK` | Vendor Account Group | String | PREF, STD |
| `ERDAT` | Date on which the Record Was Created | Date | 2020-01-01 |
| `STRAS` | Street and House Number | String | 123 Main St |
| `TELF1` | First telephone number | String | 555-0123 |
| `SMTP_ADDR` | E-Mail Address | String | contact@acme.com |
| `SPERR` | Central Posting Block | String (1) | X (Blocked) or Empty |

## MARA - Material Master
Contains general material data.

| Field | Description | Type | Example |
|-------|-------------|------|---------|
| `MATNR` | Material Number (PK) | String (18) | M00000001 |
| `MAKTX` | Material Description | String | Widget A |
| `MTART` | Material Type | String | ROH, FERT |
| `MATKL` | Material Group | String | ELECT, OFF |
| `MEINS` | Base Unit of Measure | String (3) | PC, KG |
| `ERSDA` | Created On | Date | 2020-01-01 |
| `BRGEW` | Gross Weight | Decimal | 10.5 |
| `NTGEW` | Net Weight | Decimal | 10.0 |

## EKKO - Purchasing Document Header
Contains header data for Purchase Orders (POs).

| Field | Description | Type | Example |
|-------|-------------|------|---------|
| `EBELN` | Purchasing Document Number (PK) | String (10) | PO0000001 |
| `BUKRS` | Company Code | String (4) | 1000 |
| `BSART` | Purchasing Document Type | String (2) | NB (Standard), FO (Framework) |
| `AEDAT` | Date on which the record was created | Date | 2024-01-15 |
| `LIFNR` | Vendor Account Number (FK) | String (10) | V0000001 |
| `WAERS` | Currency Key | String (3) | USD |
| `EKORG` | Purchasing Organization | String (4) | ORG1 |
| `EKGRP` | Purchasing Group | String (3) | GRP1 |
| `BEDAT` | Purchasing Document Date | Date | 2024-01-15 |

## EKPO - Purchasing Document Item
Contains line item data for POs.

| Field | Description | Type | Example |
|-------|-------------|------|---------|
| `EBELN` | Purchasing Document Number (PK, FK) | String (10) | PO0000001 |
| `EBELP` | Item Number of Purchasing Document (PK) | Integer | 10, 20 |
| `MATNR` | Material Number (FK) | String (18) | M00000001 |
| `MENGE` | Purchase Order Quantity | Decimal | 100 |
| `MEINS` | Order Unit | String (3) | PC |
| `NETPR` | Net Price | Decimal | 50.00 |
| `NETWR` | Net Order Value in PO Currency | Decimal | 5000.00 |
| `EINDT` | Item Delivery Date | Date | 2024-02-15 |
| `WERKS` | Plant | String (4) | 1000 |
| `MATKL` | Material Group | String | ELECT |
| `KONNR` | Contract Number (FK) | String (10) | C00000001 |

## EKBE - Purchasing History
Contains history of Goods Receipts (GR) and Invoice Receipts (IR).

| Field | Description | Type | Example |
|-------|-------------|------|---------|
| `EBELN` | Purchasing Document Number (PK, FK) | String (10) | PO0000001 |
| `EBELP` | Item Number (PK, FK) | Integer | 10 |
| `BEWTP` | Purchase Order History Category | String (1) | E (GR), Q (IR) |
| `BUDAT` | Posting Date in the Document | Date | 2024-02-16 |
| `MENGE` | Quantity | Decimal | 100 |
| `DMBTR` | Amount in Local Currency | Decimal | 5000.00 |
| `BELNR` | Number of Material Document | String (10) | 500000001 |
| `ACTUAL_DELIVERY_DATE` | Actual Date of Delivery | Date | 2024-02-16 |
| `HAS_ISSUE` | Quality/Quantity Issue Flag | Boolean | True/False |
| `RESPONSE_DAYS` | Vendor Response Time (Days) | Integer | 5 |
| `PAIR_ID` | Internal Mapping ID for GR/IR Pairs | Integer | 12345 |

## VENDOR_CONTRACTS - Custom Table
Tracks long-term purchasing agreements.

| Field | Description | Type | Example |
|-------|-------------|------|---------|
| `CONTRACT_ID` | Contract Number (PK) | String (10) | C00000001 |
| `LIFNR` | Vendor Number (FK) | String (10) | V0000001 |
| `MATNR` | Material Number (FK) | String (18) | M00000001 |
| `CONTRACT_PRICE` | Negotiated Price | Decimal | 45.00 |
| `VALID_FROM` | Validity Start Date | Date | 2023-01-01 |
| `VALID_TO` | Validity End Date | Date | 2023-12-31 |
| `VOLUME_COMMITMENT` | Annual Quantity Commitment | Integer | 1000 |
| `CONTRACT_TYPE` | Contract Type | String | BLANKET |
