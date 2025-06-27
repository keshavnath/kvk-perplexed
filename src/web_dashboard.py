import streamlit as st
import sqlite3
import pandas as pd
import json
import plotly.express as px

st.set_page_config(page_title="Dutch Sponsor Company Database", layout="wide")

@st.cache_data
def load_data(db_path: str):
    """Load and cache company data"""
    with sqlite3.connect(db_path) as conn:
        query = """
        SELECT 
            kvk_number,
            company_name,
            industries,
            employee_range,
            headquarters_location,
            business_description,
            confidence_score,
            homepage_url,
            linkedin_url,
            created_at
        FROM company_details 
        ORDER BY confidence_score DESC
        """
        df = pd.read_sql_query(query, conn)
        
        # Parse industries
        df['industries_list'] = df['industries'].apply(
            lambda x: json.loads(x) if x else []
        )
        df['industries_str'] = df['industries_list'].apply(
            lambda x: ', '.join(x) if x else ''
        )
        
        return df

def main():
    st.title("🏢 Dutch Company Database Dashboard")
    
    # Load data
    db_path = "./db/company_details.db"
    
    try:
        df = load_data(db_path)
        
        # Sidebar filters
        st.sidebar.header("Filters")
        
        # Confidence filter
        confidence_range = st.sidebar.slider(
            "Minimum Confidence Score",
            min_value=0.0,
            max_value=1.0,
            value=0.0,
            step=0.1
        )
        
        # Employee range filter
        employee_ranges = list(df['employee_range'].unique())
        selected_employees = st.sidebar.multiselect(
            "Employee Range",
            employee_ranges,
            default=[]
        )
        
        # Industry filter
        all_industries = set()
        for industries_list in df['industries_list']:
            all_industries.update(industries_list)
        
        selected_industries = st.sidebar.multiselect(
            "Industries",
            sorted(all_industries),
            default=[]
        )
        
        # Apply filters
        filtered_df = df[df['confidence_score'] >= confidence_range]
        
        # Employee range filter - if none selected, show all
        if selected_employees:
            filtered_df = filtered_df[filtered_df['employee_range'].isin(selected_employees)]
        
        # Industry filter - if none selected, show all
        if selected_industries:
            filtered_df = filtered_df[
                filtered_df['industries_list'].apply(
                    lambda x: any(industry in x for industry in selected_industries)
                )
            ]
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Companies", len(filtered_df))
        with col2:
            st.metric("Avg Confidence", f"{filtered_df['confidence_score'].mean():.2f}")
        with col3:
            st.metric("With Homepage", len(filtered_df[filtered_df['homepage_url'] != '']))
        with col4:
            st.metric("With LinkedIn", len(filtered_df[filtered_df['linkedin_url'] != '']))
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            # Industry distribution
            industry_counts = {}
            for industries_list in filtered_df['industries_list']:
                for industry in industries_list:
                    industry_counts[industry] = industry_counts.get(industry, 0) + 1
            
            if industry_counts:
                sorted_industries = sorted(industry_counts.items(), key=lambda x: x[1], reverse=True)#[:10]
                fig1 = px.bar(
                    x=[count for industry, count in sorted_industries],
                    y=[industry for industry, count in sorted_industries],
                    orientation='h',
                    title="Industries Distribution"
                )
                fig1.update_layout(yaxis={'categoryorder': 'total ascending'})
            else:
                fig1 = px.bar(title="No Industry Data Available")
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            # Confidence score distribution
            fig2 = px.histogram(
                filtered_df,
                x='confidence_score',
                nbins=20,
                title="Confidence Score Distribution"
            )
            st.plotly_chart(fig2, use_container_width=True)
        
        # Company table
        st.header("Company Details")
        
        # Select columns to display
        display_columns = st.multiselect(
            "Select columns to display:",
            ['kvk_number', 'company_name', 'industries_str', 'employee_range', 
             'headquarters_location', 'confidence_score', 'homepage_url', 'linkedin_url'],
            default=['company_name', 'industries_str', 'employee_range', 'confidence_score']
        )
        
        if display_columns:
            display_df = filtered_df[display_columns].copy()
            
            # Make URLs clickable
            if 'homepage_url' in display_df.columns:
                display_df['homepage_url'] = display_df['homepage_url'].apply(
                    lambda x: f'<a href="{x}" target="_blank">{x}</a>' if x else ''
                )
            
            st.write(f"Showing {len(display_df)} companies")
            st.dataframe(display_df, use_container_width=True)
            
            # Download button
            csv = display_df.to_csv(index=False)
            st.download_button(
                label="Download as CSV",
                data=csv,
                file_name="filtered_companies.csv",
                mime="text/csv"
            )
    
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")

if __name__ == "__main__":
    main()