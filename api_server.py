"""
HTTP API Server for qualityb2bpackage.com Automation
Provides REST API endpoints for integration with n8n and other tools

Endpoints:
  POST /login - Login to the website
  GET /packages - Extract tour packages
  GET /packages/<id> - Get package details
  POST /expenses - Create an expense record
  GET /program-code/<tour_code> - Find program code

Usage:
  python api_server.py [--port 8080] [--host 0.0.0.0]
"""

import asyncio
import json
import logging
import os
import argparse
from typing import Optional
from functools import wraps

from flask import Flask, request, jsonify
from flask_cors import CORS

# Import our client
from mcp_server import QualityB2BClient, CONFIG

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('api_server')

# Flask app
app = Flask(__name__)
CORS(app)

# Global client instance
client: Optional[QualityB2BClient] = None
client_lock = asyncio.Lock()


def run_async(coro):
    """Run async coroutine in sync context"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def get_client() -> QualityB2BClient:
    """Get or create the client instance"""
    global client
    async with client_lock:
        if client is None:
            client = QualityB2BClient()
            await client.initialize(headless=True)
        return client


def async_route(f):
    """Decorator to handle async routes"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        return run_async(f(*args, **kwargs))
    return wrapper


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "qb2b-automation-api"
    })


@app.route('/login', methods=['POST'])
@async_route
async def login():
    """Login to qualityb2bpackage.com"""
    try:
        c = await get_client()
        success = await c.login()
        return jsonify({
            "success": success,
            "message": "Login successful" if success else "Login failed"
        })
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/packages', methods=['GET'])
@async_route
async def get_packages():
    """Extract tour packages"""
    try:
        limit = request.args.get('limit', 50, type=int)
        c = await get_client()
        packages = await c.extract_packages(limit=limit)
        return jsonify({
            "success": True,
            "count": len(packages),
            "packages": packages
        })
    except Exception as e:
        logger.error(f"Package extraction error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/packages/<package_id>', methods=['GET'])
@async_route
async def get_package_details(package_id: str):
    """Get package details"""
    try:
        c = await get_client()
        details = await c.get_package_details(package_id)
        return jsonify({
            "success": True,
            "package": details
        })
    except Exception as e:
        logger.error(f"Package details error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/program-code/<tour_code>', methods=['GET'])
@async_route
async def find_program_code(tour_code: str):
    """Find program code from tour code"""
    try:
        c = await get_client()
        program_code = await c.find_program_code(tour_code)
        return jsonify({
            "success": program_code is not None,
            "tour_code": tour_code,
            "program_code": program_code
        })
    except Exception as e:
        logger.error(f"Program code search error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/expenses', methods=['POST'])
@async_route
async def create_expense():
    """Create an expense record"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required = ['tour_code', 'program_code', 'amount', 'pax']
        missing = [f for f in required if f not in data]
        if missing:
            return jsonify({
                "success": False,
                "error": f"Missing required fields: {missing}"
            }), 400
        
        c = await get_client()
        result = await c.create_expense(
            tour_code=data['tour_code'],
            program_code=data['program_code'],
            amount=int(data['amount']),
            pax=int(data['pax']),
            description=data.get('description', 'ค่าอุปกรณ์ออกทัวร์'),
            add_company_expense=data.get('add_company_expense', True)
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Expense creation error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/batch-expenses', methods=['POST'])
@async_route
async def create_batch_expenses():
    """Create multiple expense records"""
    try:
        data = request.get_json()
        expenses = data.get('expenses', [])
        
        if not expenses:
            return jsonify({
                "success": False,
                "error": "No expenses provided"
            }), 400
        
        c = await get_client()
        results = []
        
        for expense in expenses:
            try:
                result = await c.create_expense(
                    tour_code=expense['tour_code'],
                    program_code=expense['program_code'],
                    amount=int(expense['amount']),
                    pax=int(expense['pax']),
                    description=expense.get('description', 'ค่าอุปกรณ์ออกทัวร์'),
                    add_company_expense=expense.get('add_company_expense', True)
                )
                results.append(result)
            except Exception as e:
                results.append({
                    "success": False,
                    "tour_code": expense.get('tour_code'),
                    "error": str(e)
                })
        
        success_count = sum(1 for r in results if r.get('success'))
        
        return jsonify({
            "success": True,
            "total": len(results),
            "successful": success_count,
            "failed": len(results) - success_count,
            "results": results
        })
        
    except Exception as e:
        logger.error(f"Batch expense error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/config', methods=['GET'])
def get_config():
    """Get current configuration (without sensitive data)"""
    return jsonify({
        "base_url": CONFIG['base_url'],
        "charges_url": CONFIG['charges_url'],
        "packages_url": CONFIG['packages_url'],
        "company_name": CONFIG.get('company_name', ''),
        "company_expense_enabled": CONFIG.get('company_expense_enabled', True)
    })


@app.route('/config', methods=['PUT'])
def update_config():
    """Update configuration"""
    try:
        data = request.get_json()
        
        # Only allow updating certain fields
        allowed_fields = [
            'description', 'charge_type', 'company_expense_enabled',
            'company_name', 'company_value', 'payment_method', 'payment_type'
        ]
        
        for field in allowed_fields:
            if field in data:
                CONFIG[field] = data[field]
        
        return jsonify({
            "success": True,
            "message": "Configuration updated"
        })
        
    except Exception as e:
        logger.error(f"Config update error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='QB2B Automation API Server')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8080, help='Port to listen on')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    args = parser.parse_args()
    
    logger.info(f"Starting API server on {args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
