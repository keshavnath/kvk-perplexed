# Dutch Company Analyzer

A tool to analyze Dutch companies using their KVK numbers.

## Setup

1. Place your input CSV file in the `data` folder with columns `company_name` and `kvk_number`
2. Install requirements:
```bash
pip install -r requirements.txt
```

## Usage

Run the script from the src directory:
```bash
cd src
python main.py
```

Results will be saved in `data/results.csv`.

Note: Please respect website terms of service and rate limiting when scraping.
