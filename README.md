# KvK Company Size Analyzer

A tool to identify "big" companies in the Netherlands based on their branch/subsidiary structure using OpenCorporates data.

## Overview
This tool analyzes Dutch companies by their KvK (Chamber of Commerce) numbers to determine if they are "big" companies, defined as companies that have branches or subsidiaries listed on OpenCorporates.

## Requirements
- Python 3.7+
- Chrome browser installed
- Required Python packages:
  ```
  selenium
  beautifulsoup4
  pandas
  tqdm
  ```

## Setup
1. Clone this repository
2. Install required packages:
   ```
   pip install selenium beautifulsoup4 pandas tqdm
   ```
3. Ensure Chrome browser is installed

## Usage
Basic usage:
```bash
python src/main.py input.csv
```

Options:
- `--output`: Specify output file path (default: big_companies.csv)
- `--limit`: Process only first N companies
- `--log-file`: Specify log file location (default: runlog.txt)

Example:
```bash
python src/main.py companies.csv --limit 100 --output results.csv
```

## Input Format
The input CSV file should contain at least these columns:
- `kvk_number`: KvK registration number
- `company_name`: Company name

## Output
The script generates:
1. A CSV file containing companies identified as "big"
2. A log file with detailed processing information

## Notes
- The tool uses web scraping with Selenium, so processing speed is limited
- Includes automatic handling of various KvK number formats
- Logs scraping details to a separate file for debugging
