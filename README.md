# StockFlow Backend Case Study

## Candidate Details

**Name:** Venkateswara Rao Allaka
**Role:** Backend / Full Stack Developer Case Study Submission

---

# Project Overview

StockFlow is a B2B inventory management platform used by small businesses to manage products across multiple warehouses, track stock levels, manage suppliers, and handle inventory operations efficiently.

This case study focuses on solving real-world backend engineering challenges involving:

* Code Review & Debugging
* Database Design
* API Implementation

The goal is to build a scalable, production-ready backend system while considering business logic, maintainability, and performance.

---

# Tech Stack Used

* Python
* Flask
* SQLAlchemy
* MySQL
* PostgreSQL-compatible SQL Design
* REST API Design
* Git + GitHub

---

# Repository Structure

```text
stockflow-backend-case-study/
│
├── README.md
├── requirements.txt
├── app.py
├── models.py
├── auth.py
│
├── part1/
│   ├── create_product.py
│   └── code_review_explanation.md
│
├── part2/
│   └── schema.sql
│
├── part3/
│   └── low_stock_alerts.py
│
└── postman_collection.json
```

---

# Part 1: Code Review & Debugging

## Problem

The provided API endpoint for creating products had multiple technical and business logic issues:

* Product incorrectly linked to a single warehouse
* No SKU uniqueness validation
* Multiple database commits causing partial failures
* No transaction handling
* Missing input validation
* Price precision issues using float
* No warehouse existence validation
* No error handling
* Optional fields not handled properly
* Duplicate inventory records possible

## Solution

The corrected implementation includes:

* Proper Product ↔ Inventory normalization
* Single transaction commit
* Decimal price handling
* Validation for required fields
* Warehouse existence verification
* SKU uniqueness enforcement
* Rollback on failure
* Safe error handling
* Unique constraints for inventory mapping

This ensures production safety and database consistency.

---

# Part 2: Database Design

## Requirements Covered

* Companies can have multiple warehouses
* Products can exist across multiple warehouses
* Inventory quantity tracking
* Inventory history tracking
* Supplier relationships
* Product bundles support

## Designed Tables

* Company
* Warehouse
* Product
* Inventory
* Inventory_History
* Supplier
* Product_Supplier
* Bundle_Component

## Key Design Decisions

### Why separate Product and Inventory?

Because products can exist in multiple warehouses.

### Why Inventory History?

To maintain a complete audit trail of stock movement.

### Why Product_Supplier?

Because suppliers and products have a many-to-many relationship.

### Why unique(product_id, warehouse_id)?

To prevent duplicate inventory entries.

### Why Numeric(10,2) for price?

To avoid financial precision issues.

---

# Part 3: Low Stock Alerts API

## Endpoint

```http
GET /api/companies/{company_id}/alerts/low-stock
```

## Business Rules Implemented

* Low stock threshold varies by product
* Only recently sold products should trigger alerts
* Multiple warehouses supported
* Supplier details included for reordering
* Company-level filtering applied

## Response Includes

* Product details
* Warehouse details
* Current stock
* Threshold value
* Estimated days until stockout
* Supplier contact information

This endpoint helps businesses proactively reorder inventory before stockouts happen.

---

# Assumptions Made

Since some requirements were intentionally incomplete, the following assumptions were made:

* Recent sales activity = last 30 days
* One primary supplier is used for alerts
* Low stock threshold stored in Product table
* Company owns warehouses
* Bundles can be tracked using self-referencing product relationships
* Soft delete strategy may be implemented later if required

These assumptions are documented for clarity during live discussion.

---

# How to Run the Project

## Step 1: Clone Repository

```bash
git clone https://github.com/venkyallaka/stockflow-backend-case-study.git
cd stockflow-backend-case-study
```

---

## Step 2: Create Virtual Environment

```bash
python -m venv venv
```

Activate virtual environment:

### Windows

```bash
venv\Scripts\activate
```

### Mac/Linux

```bash
source venv/bin/activate
```

---

## Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Step 4: Configure Database

Create your MySQL database and update database configuration inside:

```python
app.py
```

Example:

```python
SQLALCHEMY_DATABASE_URI = "mysql://username:password@localhost/stockflow"
```

---

## Step 5: Run Application

```bash
python app.py
```

Server will run on:

```text
http://localhost:5000
```

---

# API Endpoints

## Create Product

```http
POST /api/products
```

Creates a new product and initializes inventory safely.

---

## Low Stock Alerts

```http
GET /api/companies/{company_id}/alerts/low-stock
```

Returns low-stock alerts with supplier details.

---

# Challenges Faced

* Handling incomplete business requirements
* Designing scalable multi-warehouse inventory architecture
* Ensuring transaction safety
* Avoiding duplicate inventory mapping
* Supporting bundle products
* Maintaining strong normalization without overengineering

These challenges were solved using production-oriented backend design principles.

---

# Final Notes

This solution prioritizes:

* Production safety
* Scalability
* Maintainability
* Clean architecture
* Business correctness
* Strong database normalization

The focus was not just to make the code work, but to design a backend system that would perform reliably in a real B2B SaaS production environment.

This case study reflects my approach to backend engineering: writing clean, reliable, and scalable systems with strong attention to business logic and long-term maintainability.

Thank you for reviewing my submission.
