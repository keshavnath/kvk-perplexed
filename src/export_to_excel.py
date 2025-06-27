import sqlite3
import pandas as pd
import json
from pathlib import Path
import argparse

def export_company_details_to_excel(db_path: str, output_path: str = "company_details.xlsx"):
    """Export company details database to Excel with multiple sheets"""
    
    with sqlite3.connect(db_path) as conn:
        # Main data sheet
        main_query = """
        SELECT 
            kvk_number,
            company_name,
            industries,
            employee_range,
            headquarters_location,
            business_description,
            ROUND(confidence_score, 2) as confidence_score,
            homepage_url,
            linkedin_url,
            DATE(created_at) as processed_date
        FROM company_details 
        ORDER BY confidence_score DESC, company_name
        """
        
        df_main = pd.read_sql_query(main_query, conn)
        
        # Parse industries JSON for better readability
        df_main['industries_parsed'] = df_main['industries'].apply(
            lambda x: ', '.join(json.loads(x)) if x else ''
        )
        df_main = df_main.drop('industries', axis=1)
        df_main = df_main.rename(columns={'industries_parsed': 'industries'})
        
        # Summary statistics
        summary_data = {
            'Metric': [
                'Total Companies',
                'High Confidence (≥0.8)',
                'Medium Confidence (0.5-0.8)',
                'Low Confidence (<0.5)',
                'Companies with Homepage',
                'Companies with LinkedIn',
                'Average Confidence Score'
            ],
            'Count': [
                len(df_main),
                len(df_main[df_main['confidence_score'] >= 0.8]),
                len(df_main[(df_main['confidence_score'] >= 0.5) & (df_main['confidence_score'] < 0.8)]),
                len(df_main[df_main['confidence_score'] < 0.5]),
                len(df_main[df_main['homepage_url'] != '']),
                len(df_main[df_main['linkedin_url'] != '']),
                round(df_main['confidence_score'].mean(), 2)
            ]
        }
        df_summary = pd.DataFrame(summary_data)
        
        # Industry breakdown
        industry_breakdown = []
        for industries_str in df_main['industries']:
            if industries_str:
                for industry in industries_str.split(', '):
                    industry_breakdown.append(industry.strip())
        
        df_industries = pd.DataFrame(industry_breakdown, columns=['Industry'])
        df_industries = df_industries['Industry'].value_counts().reset_index()
        df_industries.columns = ['Industry', 'Count']
        
        # Employee range distribution
        df_employees = df_main['employee_range'].value_counts().reset_index()
        df_employees.columns = ['Employee Range', 'Count']
        
        # Export to Excel with multiple sheets
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            df_main.to_excel(writer, sheet_name='Company Details', index=False)
            df_summary.to_excel(writer, sheet_name='Summary', index=False)
            df_industries.to_excel(writer, sheet_name='Industries', index=False)
            df_employees.to_excel(writer, sheet_name='Employee Ranges', index=False)
        
        print(f"Exported {len(df_main)} companies to {output_path}")
        return output_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Export company details to Excel')
    parser.add_argument('--db-path', default='./db/company_details.db', help='Database path')
    parser.add_argument('--output', default='company_details.xlsx', help='Output Excel file')
    
    args = parser.parse_args()
    export_company_details_to_excel(args.db_path, args.output)