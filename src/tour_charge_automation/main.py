"""
Main Orchestration Script for Tour Charge Automation using CrewAI
This script coordinates multiple AI agents to automate the tour charge expense form.
"""

import os
import csv
import argparse
import logging
from datetime import datetime
from typing import List, Dict, Any

from crewai import Crew, Process
from dotenv import load_dotenv

from .agents import create_all_agents
from .tasks import create_all_tasks_for_entry
from .tools.browser_tools import BrowserManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_csv_data(csv_path: str, start: int = 0, limit: int = None) -> List[Dict[str, Any]]:
    """
    Load tour data from CSV file.
    
    Args:
        csv_path: Path to the CSV file
        start: Starting row index (0-based)
        limit: Maximum number of rows to load
    
    Returns:
        List of dictionaries with tour data
    """
    entries = []
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i < start:
                continue
            if limit and len(entries) >= limit:
                break
            
            # Extract and clean data
            tour_code = row.get('รหัสทัวร์', '').strip()
            pax_str = row.get('จำนวนลูกค้า หัก หนท.', '0').strip()
            amount_str = row.get('ยอดเบิก', '0').strip()
            
            # Parse numeric values
            try:
                pax = int(float(pax_str)) if pax_str else 0
                amount = float(amount_str.replace(',', '')) if amount_str else 0
            except ValueError:
                logger.warning(f"⚠️ Skipping row {i}: Invalid data")
                continue
            
            if tour_code and amount > 0:
                entries.append({
                    'tour_code': tour_code,
                    'pax': pax,
                    'amount': amount,
                    'row_index': i
                })
    
    return entries


def process_single_entry(entry: Dict[str, Any], agents: dict, verbose: bool = True) -> Dict[str, Any]:
    """
    Process a single tour entry using the CrewAI workflow.
    
    Args:
        entry: Dictionary with tour_code, pax, and amount
        agents: Dictionary of agent instances
        verbose: Whether to show detailed output
    
    Returns:
        Result dictionary with status and expense number
    """
    tour_code = entry['tour_code']
    pax = entry['pax']
    amount = entry['amount']
    
    logger.info(f"\n{'='*60}")
    logger.info(f"🚀 Processing: {tour_code} | PAX: {pax} | Amount: {amount} THB")
    logger.info(f"{'='*60}")
    
    try:
        # Create tasks for this entry
        tasks = create_all_tasks_for_entry(agents, tour_code, pax, amount)
        
        # Create the crew
        crew = Crew(
            agents=list(agents.values()),
            tasks=tasks,
            process=Process.sequential,
            verbose=verbose
        )
        
        # Execute the workflow
        result = crew.kickoff()
        
        # Parse the result for expense number
        expense_no = None
        result_str = str(result)
        if 'C' in result_str:
            import re
            match = re.search(r'C\d{6}-\d{6}', result_str)
            if match:
                expense_no = match.group(0)
        
        return {
            'tour_code': tour_code,
            'pax': pax,
            'amount': amount,
            'status': 'SUCCESS',
            'expense_no': expense_no or '',
            'result': result_str[:200],
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error processing {tour_code}: {e}")
        return {
            'tour_code': tour_code,
            'pax': pax,
            'amount': amount,
            'status': 'FAILED',
            'expense_no': '',
            'error': str(e)[:100],
            'timestamp': datetime.now().isoformat()
        }


def run_automation(csv_path: str, start: int = 0, limit: int = 3, 
                   verbose: bool = True, headless: bool = False) -> List[Dict[str, Any]]:
    """
    Run the complete automation workflow.
    
    Args:
        csv_path: Path to the CSV file with tour data
        start: Starting row index
        limit: Maximum entries to process
        verbose: Whether to show detailed output
        headless: Whether to run browser in headless mode
    
    Returns:
        List of result dictionaries
    """
    # Load environment variables
    load_dotenv()
    
    # Verify OpenAI API key
    if not os.getenv('OPENAI_API_KEY') or os.getenv('OPENAI_API_KEY') == 'your_openai_api_key_here':
        logger.error("❌ Please set your OPENAI_API_KEY in the .env file")
        return []
    
    # Load data
    entries = load_csv_data(csv_path, start, limit)
    logger.info(f"📊 Loaded {len(entries)} entries from CSV")
    
    if not entries:
        logger.warning("⚠️ No entries to process")
        return []
    
    # Create agents (shared across all entries for efficiency)
    agents = create_all_agents()
    logger.info(f"🤖 Created {len(agents)} AI agents")
    
    results = []
    browser_manager = BrowserManager()
    
    try:
        for i, entry in enumerate(entries):
            logger.info(f"\n[{i+1}/{len(entries)}] Starting entry...")
            
            result = process_single_entry(entry, agents, verbose)
            results.append(result)
            
            # Log progress
            if result['status'] == 'SUCCESS':
                logger.info(f"✅ Completed: {entry['tour_code']}")
                if result.get('expense_no'):
                    logger.info(f"📋 Expense No: {result['expense_no']}")
            else:
                logger.error(f"❌ Failed: {entry['tour_code']}")
    
    finally:
        # Always close browser
        browser_manager.close()
        logger.info("🌐 Browser closed")
    
    # Save results
    output_file = f"crewai_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    save_results(results, output_file)
    
    # Summary
    success_count = sum(1 for r in results if r.get('status') == 'SUCCESS')
    logger.info(f"\n📊 SUMMARY: {success_count}/{len(results)} successful")
    logger.info(f"📁 Results saved to: {output_file}")
    
    return results


def save_results(results: List[Dict[str, Any]], output_file: str):
    """Save results to CSV file."""
    if not results:
        return
    
    fieldnames = ['tour_code', 'pax', 'amount', 'status', 'expense_no', 'timestamp', 'error', 'result']
    
    with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(results)


def main():
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description='Tour Charge Automation with CrewAI Multi-Agent System'
    )
    parser.add_argument(
        '--csv', 
        type=str, 
        default='ยอดเบิกอุปกรณ์.csv',
        help='Path to the CSV file with tour data'
    )
    parser.add_argument(
        '--start', 
        type=int, 
        default=0,
        help='Starting row index (0-based)'
    )
    parser.add_argument(
        '--limit', 
        type=int, 
        default=3,
        help='Maximum number of entries to process'
    )
    parser.add_argument(
        '--verbose', 
        action='store_true',
        default=True,
        help='Enable verbose output'
    )
    parser.add_argument(
        '--headless', 
        action='store_true',
        default=False,
        help='Run browser in headless mode'
    )
    
    args = parser.parse_args()
    
    # Run automation
    results = run_automation(
        csv_path=args.csv,
        start=args.start,
        limit=args.limit,
        verbose=args.verbose,
        headless=args.headless
    )
    
    return results


if __name__ == "__main__":
    main()
