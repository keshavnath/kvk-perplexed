import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import sqlite3
from pathlib import Path
import sys
import os
import json

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.phase2_processor import Phase2Processor
from src.models import CompanyDetails
from src.company_details_db import CompanyDetailsDB

class TestPhase2Processor(unittest.TestCase):
    def setUp(self):
        # Create temporary databases
        self.temp_dir = tempfile.mkdtemp()
        self.phase1_db_path = Path(self.temp_dir) / "test_companies.db"
        self.phase2_db_path = Path(self.temp_dir) / "test_company_details.db"
        
        # Setup Phase 1 test database
        self.setup_phase1_db()
        
        # Mock PerplexityClient to avoid API calls
        with patch('src.phase2_processor.PerplexityClient') as mock_client:
            self.mock_perplexity = Mock()
            mock_client.return_value = self.mock_perplexity
            self.processor = Phase2Processor(
                str(self.phase1_db_path), 
                str(self.phase2_db_path)
            )

    def setup_phase1_db(self):
        """Setup test Phase 1 database with sample data"""
        with sqlite3.connect(self.phase1_db_path) as conn:
            conn.execute('''
                CREATE TABLE companies (
                    company_name TEXT,
                    kvk_number TEXT PRIMARY KEY,
                    has_branches INTEGER
                )
            ''')
            
            # Insert test data
            test_companies = [
                ("Company With Branches A", "12345678", 1),
                ("Company With Branches B", "23456789", 1),
                ("Company Without Branches", "34567890", 0),
                ("Failed Company", "45678901", -1),
                ("Another Branch Company", "56789012", 1)
            ]
            
            conn.executemany(
                "INSERT INTO companies VALUES (?, ?, ?)", 
                test_companies
            )
            conn.commit()

    def tearDown(self):
        # Cleanup temporary files
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_get_companies_with_branches(self):
        """Test fetching companies with branches from Phase 1 DB"""
        companies = self.processor.get_companies_with_branches()
        
        # Should return 3 companies with has_branches = 1
        self.assertEqual(len(companies), 3)
        
        # Check company names
        company_names = [name for name, _ in companies]
        self.assertIn("Company With Branches A", company_names)
        self.assertIn("Company With Branches B", company_names)
        self.assertIn("Another Branch Company", company_names)
        
        # Should not include companies without branches
        self.assertNotIn("Company Without Branches", company_names)

    def test_get_unprocessed_companies(self):
        """Test getting unprocessed companies"""
        # Initially, all companies should be unprocessed
        unprocessed = self.processor.get_unprocessed_companies()
        self.assertEqual(len(unprocessed), 3)
        
        # Process one company manually
        test_details = CompanyDetails(
            industries=["Technology & Software"],
            employee_range="11-50",
            headquarters_location="Amsterdam, Netherlands",
            business_description="Test company",
            confidence_score=0.8,
            homepage_url="https://test.com",
            linkedin_url="https://linkedin.com/company/test"
        )
        
        self.processor.phase2_db.store_company_details(
            "12345678", "Company With Branches A", test_details
        )
        
        # Now should have 2 unprocessed
        unprocessed = self.processor.get_unprocessed_companies()
        self.assertEqual(len(unprocessed), 2)

    @patch('src.phase2_processor.time.sleep')  # Skip delays in tests
    def test_process_company_success(self, mock_sleep):
        """Test successful company processing"""
        # Mock successful Perplexity response
        mock_details = CompanyDetails(
            industries=["Technology & Software", "Financial Services"],
            employee_range="201-500",
            headquarters_location="Rotterdam, Netherlands",
            business_description="A leading tech company",
            confidence_score=0.9,
            homepage_url="https://example.com",
            linkedin_url="https://linkedin.com/company/example"
        )
        
        self.mock_perplexity.get_company_details.return_value = mock_details
        
        # Process company
        result = self.processor.process_company("Test Company", "12345678")
        
        # Should succeed
        self.assertTrue(result)
        
        # Check if stored in database
        self.assertTrue(self.processor.phase2_db.has_been_processed("12345678"))

    def test_process_company_low_confidence(self):
        """Test handling of low confidence responses"""
        # Mock low confidence response
        mock_details = CompanyDetails(
            industries=["Technology & Software"],
            employee_range="1-10",
            headquarters_location="Unknown",
            business_description="Unknown company",
            confidence_score=0.05,  # Very low confidence
            homepage_url="",
            linkedin_url=""
        )
        
        self.mock_perplexity.get_company_details.return_value = mock_details
        
        # Process company
        result = self.processor.process_company("Unknown Company", "99999999")
        
        # Should fail due to low confidence
        self.assertFalse(result)
        
        # Should not be stored in database
        self.assertFalse(self.processor.phase2_db.has_been_processed("99999999"))

    def test_process_company_api_failure(self):
        """Test handling of API failures"""
        # Mock API failure
        self.mock_perplexity.get_company_details.return_value = None
        
        # Process company
        result = self.processor.process_company("Failed Company", "88888888")
        
        # Should fail
        self.assertFalse(result)

    @patch('src.phase2_processor.time.sleep')
    def test_batch_processing(self, mock_sleep):
        """Test batch processing functionality"""
        # Mock successful responses for all companies
        mock_details = CompanyDetails(
            industries=["Manufacturing"],
            employee_range="51-200",
            headquarters_location="Utrecht, Netherlands",
            business_description="Manufacturing company",
            confidence_score=0.7,
            homepage_url="https://manufacturer.com",
            linkedin_url=""
        )
        
        self.mock_perplexity.get_company_details.return_value = mock_details
        
        # Run batch processing with limit
        self.processor.run_batch_processing(max_companies=2, delay_seconds=0)
        
        # Check that companies were processed
        companies = self.processor.phase2_db.get_companies_by_confidence(0.0)
        self.assertEqual(len(companies), 2)

class TestCompanyDetailsDB(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_details.db"
        self.db = CompanyDetailsDB(str(self.db_path))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_store_and_retrieve_company_details(self):
        """Test storing and retrieving company details"""
        details = CompanyDetails(
            industries=["Technology & Software", "Education"],
            employee_range="1001-5000",
            headquarters_location="The Hague, Netherlands",
            business_description="Educational technology platform",
            confidence_score=0.85,
            homepage_url="https://edtech.com",
            linkedin_url="https://linkedin.com/company/edtech"
        )
        
        # Store details
        self.db.store_company_details("11111111", "EdTech Company", details)
        
        # Check if processed
        self.assertTrue(self.db.has_been_processed("11111111"))
        
        # Retrieve by confidence
        companies = self.db.get_companies_by_confidence(0.8)
        self.assertEqual(len(companies), 1)
        
        # Check stored data
        stored = companies[0]
        self.assertEqual(stored[0], "11111111")  # kvk_number
        self.assertEqual(stored[1], "EdTech Company")  # company_name
        
        # Check JSON parsing of industries
        stored_industries = json.loads(stored[2])
        self.assertEqual(stored_industries, ["Technology & Software", "Education"])

    def test_confidence_filtering(self):
        """Test filtering by confidence score"""
        # Store companies with different confidence scores
        high_confidence = CompanyDetails(
            industries=["Financial Services"],
            employee_range="501-1000",
            headquarters_location="Amsterdam, Netherlands",
            business_description="High confidence company",
            confidence_score=0.9,
            homepage_url="https://highconf.com",
            linkedin_url=""
        )
        
        low_confidence = CompanyDetails(
            industries=["Manufacturing"],
            employee_range="11-50",
            headquarters_location="Groningen, Netherlands",
            business_description="Low confidence company",
            confidence_score=0.3,
            homepage_url="",
            linkedin_url=""
        )
        
        self.db.store_company_details("22222222", "High Conf Co", high_confidence)
        self.db.store_company_details("33333333", "Low Conf Co", low_confidence)
        
        # Test different confidence thresholds
        all_companies = self.db.get_companies_by_confidence(0.0)
        self.assertEqual(len(all_companies), 2)
        
        high_conf_only = self.db.get_companies_by_confidence(0.8)
        self.assertEqual(len(high_conf_only), 1)
        self.assertEqual(high_conf_only[0][1], "High Conf Co")

class TestModels(unittest.TestCase):
    def test_company_details_validation(self):
        """Test CompanyDetails model validation"""
        # Valid model
        valid_details = CompanyDetails(
            industries=["Technology & Software"],
            employee_range="11-50",
            headquarters_location="Amsterdam, Netherlands",
            business_description="Valid company",
            confidence_score=0.8,
            homepage_url="https://valid.com",
            linkedin_url="https://linkedin.com/company/valid"
        )
        
        self.assertEqual(valid_details.confidence_score, 0.8)
        self.assertEqual(len(valid_details.industries), 1)

    def test_invalid_industry_validation(self):
        """Test validation of invalid industries"""
        from pydantic import ValidationError
        
        with self.assertRaises(ValidationError):
            CompanyDetails(
                industries=["Invalid Industry"],  # Not in predefined list
                employee_range="11-50",
                headquarters_location="Amsterdam, Netherlands",
                business_description="Invalid industry",
                confidence_score=0.8
            )

    def test_invalid_employee_range_validation(self):
        """Test validation of invalid employee ranges"""
        from pydantic import ValidationError
        
        with self.assertRaises(ValidationError):
            CompanyDetails(
                industries=["Technology & Software"],
                employee_range="invalid-range",  # Not in predefined list
                headquarters_location="Amsterdam, Netherlands",
                business_description="Invalid range",
                confidence_score=0.8
            )

if __name__ == '__main__':
    unittest.main()
