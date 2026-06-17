# FMCG AI Business Insights Assistant

An AI-powered conversational analytics assistant designed for the Fast-Moving Consumer Goods (FMCG) Beverages category. The system enables business users to obtain sales, promotion, inventory, and regional performance insights using natural language queries without requiring analyst intervention.

---

# Problem Statement

Business teams frequently request:

* Promotional performance summaries
* Inventory movement insights
* Regional sales comparisons
* Product-level performance analysis
* Campaign effectiveness reports

Traditionally, these requests require manual dashboard creation and ad-hoc analysis by data teams, resulting in:

* Slow decision-making
* Repetitive reporting effort
* High dependency on analysts
* Limited self-service analytics

This project addresses these challenges by providing an AI-powered assistant capable of generating business insights conversationally.

---

# Solution Overview

The FMCG AI Assistant combines:

* Synthetic FMCG business datasets
* Relational database architecture
* AI-powered query interpretation
* Automated business insight generation

Users can ask questions such as:

* Which promotion generated the highest revenue?
* Compare sales across regions.
* Which products frequently experience stockouts?
* How did promotions impact product sales?
* Which stores are underperforming?

The assistant converts business questions into structured database queries and returns human-readable insights.

---

# System Architecture

```text
User
  │
  ▼
Frontend (Streamlit)
  │
  ▼
AI Layer (Claude / Gemini)
  │
  ▼
Query Engine
  │
  ▼
SQLite / PostgreSQL Database
  │
  ▼
Analytics Layer
  │
  ▼
Business Insights Response
```

---

# Dataset Design

The solution uses four interconnected datasets.

## 1. Product Master

Contains beverage product information.

Fields:

* product_id
* product_name
* brand
* category
* sub_category
* pack_size_ml
* unit_price

Dataset Size:

* 18 products
* 5 categories

---

## 2. Store Master

Contains retail location information.

Fields:

* store_id
* store_name
* region
* city
* store_format

Dataset Size:

* 40 stores
* 4 regions

---

## 3. Sales & Promotions

Contains weekly sales performance.

Fields:

* week_start_date
* product_id
* store_id
* region
* units_sold
* revenue
* promotion_flag
* promotion_type
* discount_pct

Dataset Characteristics:

* 24 weeks of history
* Promotion campaigns
* Seasonal trends
* Regional demand variations

---

## 4. Inventory

Tracks weekly inventory movement.

Fields:

* week_start_date
* product_id
* store_id
* opening_stock
* units_received
* units_sold
* closing_stock
* stockout_flag

Dataset Characteristics:

* Replenishment cycles
* Stockout events
* Inventory drawdown analysis

---

# Synthetic Data Generation Strategy

The datasets were generated using a simulation-based approach rather than random value generation.

The simulation includes:

### Promotion Effects

Supported promotion types:

* Price Cut
* BOGO
* Bundle
* Display Feature

Each promotion generates realistic demand uplift.

---

### Seasonal Demand

Demand varies across weeks based on category:

* Water demand increases during warmer periods
* Energy drinks show seasonal growth
* Juice and Dairy remain relatively stable

---

### Regional Variation

Demand differs across:

* North
* South
* East
* West

This enables meaningful regional analysis.

---

### Inventory Simulation

Inventory and sales are generated together to ensure consistency.

Features:

* Reorder point inventory policy
* Lead-time replenishment
* Stockout events
* Lost sales scenarios

This prevents unrealistic situations where sales exceed available inventory.

---

# Technology Stack

## Programming Language

* Python 3.x

## Backend

* FastAPI

## Frontend

* Streamlit

## Database

* SQLite
* PostgreSQL

## AI Layer

* Claude
* Gemini

## Development Tools

* ChatGPT
* Claude
* GitHub

---

# Project Structure

```text
fmcg-ai-assistant/
│
├── data/
│   └── raw/
│       ├── products.csv
│       ├── stores.csv
│       ├── sales.csv
│       └── inventory.csv
│
├── database/
│   ├── schema_sqlite.sql
│   ├── schema_postgres.sql
│   ├── load_data.py
│   └── fmcg.db
│
├── generators/
│   ├── generate_products.py
│   ├── generate_stores.py
│   ├── generate_sales_inventory.py
│   └── generate_all.py
│
├── app/
│   ├── frontend/
│   ├── backend/
│   └── llm/
│
├── docs/
│
├── requirements.txt
│
└── README.md
```

---

# Installation

Clone the repository:

```bash
git clone https://github.com/your-username/fmcg-ai-assistant.git
cd fmcg-ai-assistant
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

# Generate Data

Run:

```bash
python generate_all.py
```

Generated files:

```text
products.csv
stores.csv
sales.csv
inventory.csv
```

---

# Build Database

Run:

```bash
python load_data.py
```

This will:

* Create the SQLite database
* Load all datasets
* Validate data integrity
* Verify foreign key relationships

---

# Example Business Questions

The assistant is designed to answer:

### Promotions

* Which promotion generated the highest revenue?
* How effective was BOGO compared to Price Cut?

### Sales

* Which category generated the highest sales?
* What were the top-performing products?

### Inventory

* Which products experienced the most stockouts?
* Which stores have inventory issues?

### Regional Analysis

* Compare North and South region performance.
* Which region generated the highest revenue?

### Store Performance

* Which stores underperformed during promotions?
* Which store format performs best?

---

# Major Technical Challenge

The most significant challenge was ensuring consistency between sales and inventory datasets.

Initially, sales and inventory were generated independently, creating unrealistic business situations where sales exceeded available inventory.

This issue was resolved by implementing a unified simulation engine that generates both datasets simultaneously. Inventory availability directly influences sales, creating realistic stockout and replenishment scenarios.

---

# Future Improvements

Version 2.0 could include:

1. Real-time database integration
2. Multi-agent AI architecture
3. Forecasting and demand prediction models
4. Dashboard visualizations
5. Advanced SQL generation and query validation
6. Cloud-native deployment with PostgreSQL

---

# Key Learnings

* Designing realistic synthetic datasets requires business-aware simulation logic.
* Data consistency is critical for trustworthy AI-generated insights.
* Inventory and sales systems should be modeled together.
* AI assistants must be grounded in database results to reduce hallucinations.
* Modular architectures improve scalability and maintainability.

---

# Author

Durga Prasad

B.E. Artificial Intelligence & Machine Learning

Chaitanya Bharathi Institute of Technology (CBIT)

Hyderabad, India

---

# License

This project was developed as part of an AI Engineering Assessment for educational and evaluation purposes.
