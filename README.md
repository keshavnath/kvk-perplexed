# KvK Company Size Analyzer

A tool for analyzing Dutch companies based on their branch structure and collecting detailed company information using OpenCorporates and Perplexity.

## Overview
This project consists of three main phases:
1. **Phase 1 (Branch Analysis)**: Identifies "big" companies by analyzing their branch/subsidiary structure using OpenCorporates data
2. **Phase 2 (Company Details)**: Collects detailed information about identified big companies using Perplexity, including industry, employee estimates, and business intelligence
3. **Phase 3 (Export & Visualization)**: Exports and visualizes the enriched data through Excel reports and interactive web dashboards

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

### Phase 1: Branch Analysis
Basic usage:
```bash
python src/main.py input.csv
```

Options:
- `--db-path`: Specify SQLite database path (default: ./db/companies.db)
- `--start-index`: Starting row index to process (inclusive)
- `--end-index`: Ending row index to process (exclusive)
- `--log-dir`: Directory to store log files (default: ./logs/kvk_scraper_TIMESTAMP_pidNUM/)
- `--retry-failed`: Retry processing companies that previously failed

Example:
```bash
python src/main.py companies.csv --start-index 100 --retry-failed
```

### Phase 2: Perplexity Analysis
Process companies with branches to get detailed information:

```bash
python src/phase2_processor.py
```

Options:
- `--phase1-db`: Path to Phase 1 database (default: ./db/companies.db)
- `--phase2-db`: Path to Phase 2 database (default: ./db/company_details.db)
- `--max-companies`: Maximum number of companies to process
- `--delay`: Delay between API calls in seconds (default: 1.0)
- `--log-dir`: Directory for log files

Examples:
```bash
# Process all companies with branches
python src/phase2_processor.py

# Process only 10 companies with 2-second delays
python src/phase2_processor.py --max-companies 10 --delay 2.0

# Use custom database paths
python src/phase2_processor.py --phase1-db ./data/companies.db --phase2-db ./data/details.db
```

**Note**: Before running Phase 2, ensure you have:
1. A `.env` file with your Perplexity API key:
   ```
   PERPLEXITY_API_KEY=your_api_key_here
   PERPLEXITY_MODEL=sonar
   ```
2. Completed Phase 1 processing with companies that have branches

### Phase 3: Data Export and Visualization
Export and visualize the enriched company data from Phase 2:

#### Excel Export
Export company details to Excel with multiple sheets for analysis:
```bash
python src/export_to_excel.py
```

Options:
- `--db-path`: Path to company details database (default: ./db/company_details.db)
- `--output`: Output Excel filename (default: company_details.xlsx)

Example:
```bash
python src/export_to_excel.py --db-path ./db/company_details.db --output my_companies.xlsx
```

The Excel file includes:
- **Company Details**: Main data with parsed industries
- **Summary**: Processing statistics and metrics
- **Industries**: Industry breakdown and counts
- **Employee Ranges**: Employee range distribution

#### Interactive Web Dashboard
Launch an interactive web dashboard to explore and filter company data:
```bash
pip install streamlit plotly
streamlit run src/web_dashboard.py
```

The dashboard features:
- Real-time filtering by confidence score, employee range, and industries
- Interactive charts showing industry and confidence score distributions
- Downloadable filtered results as CSV
- Customizable column display
- Company metrics and statistics

**Note**: The web dashboard will open in your browser at `http://localhost:8501`

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

## Logging
The script creates separate log files for each component:
- `scraper.log`: Company scraping and branch detection logs
- `database.log`: Database operations and storage logs
- `proxy.log`: Proxy fetching, validation and rotation logs

All logs are stored in a timestamped directory:
```
logs/
    kvk_scraper_YYYYMMDD_HHMMSS_pidNUM/
        scraper.log
        database.log
        proxy.log
```

## Testing
Run all tests:
```bash
python -m pytest
```

Run specific test categories using markers:
```bash
pytest -m rate_limit     # Only rate limit tests
pytest -m branches       # Only branch detection tests  
pytest -m phase2         # Only phase 2 processing tests
```

Run tests by name matching:
```bash
pytest -k "rate"        # Run any test with "rate" in the name
pytest -k "TestPhase2"  # Run Phase 2 processor tests
pytest -k "phase2"      # Run all Phase 2 related tests
```

Test files:
- `test_scraper.py`: Tests for scraping and rate limit detection
- `test_proxy_manager.py`: Tests for proxy handling
- `test_phase2.py`: Tests for Phase 2 processing, Perplexity integration, and data models

## Project Status

### Currently Implemented
- Company size determination through branch analysis
- Persistent SQLite storage of results
- Failed result tracking and retry capability
- Detailed logging system
- Progress tracking and statistics
- **Phase 2: Perplexity integration for detailed company analysis**
- **Structured data extraction with confidence scoring**

### Phase 2 Features
- Integration with Perplexity API for detailed company research
- Industry classification from predefined categories
- Employee count estimation in structured ranges
- Headquarters location identification
- Business description generation
- Confidence scoring for data quality assessment
- Separate database for enriched company data

## Technical Details

### Phase 1 Database Schema
The SQLite database currently stores:
- Company name
- KvK number
- Branch status (true/false/-1 for failed checks)

### Phase 2 Database Schema
Extended company details database includes:
- KvK number (cross-reference key)
- Company name
- Industry classifications (1-3 categories)
- Employee range estimates
- Headquarters location
- Business description
- Confidence score (0.0-1.0)
- Timestamps for data tracking

### Supported Industries
Technology & Software, Financial Services, Manufacturing, Healthcare & Pharmaceuticals, Energy & Utilities, Construction & Real Estate, Transportation & Logistics, Retail & E-commerce, Food & Beverages, Education, Professional Services, Media & Entertainment, Telecommunications, Agriculture, Tourism & Hospitality, Automotive, Chemical & Materials, Aerospace & Defense, Government & Public Sector, Non-profit

### Employee Ranges
1-10, 11-50, 51-200, 201-500, 501-1000, 1001-5000, 5000+

## Notes
- Processing speed is limited due to web scraping
- Failed checks (None results) are stored as -1 in the database
- Use --retry-failed to reprocess previously failed checks
- Logs are automatically stored in ./logs directory with timestamps
