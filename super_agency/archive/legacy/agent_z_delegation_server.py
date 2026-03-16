#!/usr/bin/env python3
"""
AGENT Z AZ PRIME Delegation Server
Handles work delegation from AGENT X HELIX on macOS
"""

import json
import logging
import os
from datetime import datetime

from flask import Flask, jsonify, request

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AgentZDelegationServer")

app = Flask(__name__)

# Initialize AGENT Z AZ PRIME if available
try:
    from agent_z_az_prime import get_agent_z_az_prime
    agent_z = get_agent_z_az_prime()
    logger.info("AGENT Z AZ PRIME initialized for delegation server")
except ImportError:
    agent_z = None
    logger.warning("AGENT Z AZ PRIME not available")

@app.route('/status')
def get_status():
    """Get delegation server status"""
    if agent_z:
        return jsonify({
            'status': 'active',
            'agent': 'AGENT_Z_AZ_PRIME',
            'platform': 'Windows_Full_Compute',
            'capabilities': agent_z.capabilities,
            'timestamp': datetime.now().isoformat()
        })
    return jsonify({
        'status': 'limited',
        'agent': 'AGENT_Z_AZ_PRIME',
        'reason': 'Agent not fully initialized',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/delegate', methods=['POST'])
def delegate_work():
    """Handle work delegation from AGENT X HELIX"""
    try:
        work_data = request.get_json()
        if not work_data:
            return jsonify({'status': 'error', 'message': 'No work data received'})

        logger.info(f"Received delegated work: {work_data.get('action', 'unknown')}")

        if agent_z:
            # Process the delegated work
            result = agent_z.process_delegated_work(work_data)
            return jsonify({
                'status': 'processed',
                'result': result,
                'timestamp': datetime.now().isoformat()
            })
        else:
            # Simulate processing without full agent
            return jsonify({
                'status': 'simulated_processing',
                'action': work_data.get('action'),
                'message': 'Processed by delegation server (limited mode)',
                'timestamp': datetime.now().isoformat()
            })

    except Exception as e:
        logger.error(f"Delegation processing error: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        })

@app.route('/matrix_monitor')
def get_matrix_monitor_data():
    """Get MATRIX MONITOR data for cross-platform sync"""
    if agent_z:
        return jsonify(agent_z.get_matrix_monitor_data())
    return jsonify({
        'status': 'limited',
        'message': 'MATRIX MONITOR data not available',
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    port = int(os.getenv('AGENT_Z_PORT', '5002'))
    logger.info(f"Starting AGENT Z AZ PRIME delegation server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)

