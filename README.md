# KvK Company Size Analyzer

A tool for analyzing Dutch companies based on their branch structure and collecting detailed company information using OpenCorporates and Perplexity.

## Overview
This project consists of two main phases:
1. **Current Phase (Branch Analysis)**: Identifies "big" companies by analyzing their branch/subsidiary structure using OpenCorporates data
2. **Future Phase (Company Details)**: Will collect detailed information about identified big companies using Perplexity, including:
   - Location and geographic distribution
   - Industry sector and subsectors
   - Company size estimates (employees, revenue)
   - Additional business intelligence

## Requirements
- Python 3.7+
- Chrome browser installed
- Required Python packages (see requirements.txt)

## Setup
1. Clone this repository
2. Install required packages:
   ```
   pip install -r requirements.txt
   ```
3. Ensure Chrome browser is installed
4. Create required directories:
   ```
   mkdir -p logs db
   ```

## Usage
Basic usage:
```bash
python src/main.py input.csv
```

Options:
- `--db-path`: Specify SQLite database path (default: ./db/companies.db)
- `--limit`: Process only first N companies
- `--log-file`: Specify log file location (default: ./logs/kvk_scraper_TIMESTAMP_pidNUM.log)
- `--retry-failed`: Retry processing companies that previously failed

Example:
```bash
python src/main.py companies.csv --limit 100 --retry-failed
```

## Input Format
The input CSV file should contain at least these columns:
- `kvk_number`: KvK registration number
- `company_name`: Company name

## Output
The script:
1. Stores results in an SQLite database with company information:
   - Company name
   - KvK number
   - Has branches status (true/false/-1 for failed checks)
2. Generates detailed logs in the `logs` directory
3. Provides processing statistics at completion

## Features
- Automatic handling of various KvK number formats
- Persistent storage in SQLite database
- Failed result tracking (-1 in database)
- Ability to retry previously failed checks
- Detailed logging with timestamp-based filenames
- Progress bar with live statistics

## Project Status

### Currently Implemented
- Company size determination through branch analysis
- Persistent SQLite storage of results
- Failed result tracking and retry capability
- Detailed logging system
- Progress tracking and statistics

### Planned Features
- Integration with Perplexity for detailed company analysis
- Extended database schema for company details
- Rich company profiles including:
  - Geographic data
  - Industry classification
  - Size metrics
  - Business relationships
- Analysis and export tools for collected data

## Technical Details

### Current Database Schema
The SQLite database currently stores:
- Company name
- KvK number
- Branch status (true/false/-1 for failed checks)

### Future Schema Extensions (Planned)
Will be extended to include:
- Company location data
- Industry classifications
- Size indicators
- Last update timestamps
- Data confidence metrics

## Notes
- Processing speed is limited due to web scraping
- Failed checks (None results) are stored as -1 in the database
- Use --retry-failed to reprocess previously failed checks
- Logs are automatically stored in ./logs directory with timestamps
