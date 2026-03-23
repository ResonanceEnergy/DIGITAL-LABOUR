#!/usr/bin/env python3
"""
YouTube Video Enrichment Script
Extracts and enriches YouTube video transcripts using local LLM
"""

import json
import os
import requests
import sys
from datetime import datetime
from pathlib import Path

def main():
    if len(sys.argv) != 4:
        print("Usage: enrich.py <base_dir> <vid> <url>")
        sys.exit(1)

    base_dir_path = sys.argv[1]
    vid = sys.argv[2]
    url = sys.argv[3]

    base_dir = Path(base_dir_path)

    # Read transcript
    transcript_file = base_dir / 'raw.txt'
    if not transcript_file.exists():
        print('ERROR: Transcript file not found')
        sys.exit(1)

    with open(transcript_file, 'r', encoding='utf-8') as f:
        transcript = f.read()

    # Local LLM enrichment via Ollama (default) or other local API
    llm_url = os.environ.get(
        'LOCAL_LLM_URL', 'http://localhost:11434/api/generate')
    model = os.environ.get('LOCAL_LLM_MODEL', 'llama2')

    # Truncate transcript if too long (keep first 10k chars for summary)
    max_chars = 10000
    if len(transcript) > max_chars:
        transcript = transcript[:max_chars] + '...'

    prompt = f'''Analyze this YouTube video transcript and provide a structured enrichment. Focus on the Resonance Energy principles: Local-first, Consent & Control, Provenance-first, Unit Economics, Resilience, Ethical Rails, Council Governance, Do Less Go Deeper.

Transcript:
{transcript}

Provide a JSON response with:
- abstract_120w: 120-word summary
- key_insights: array of key insights
- claims: array of claims made
- entities: array of named entities
- action_items: array of actionable items
- confidence: low/medium/high
- doctrine_map: { principles: [...], themes: [...]} 
- provenance: { ingested_at: timestamp, initiator: 'DIGITAL LABOUR Pipeline'} 

JSON only, no markdown:
'''

    try:
        response = requests.post(llm_url, json={
            'model': model,
            'prompt': prompt,
            'stream': False
        }, timeout=60)

        if response.status_code == 200:
            result = response.json()
            # Extract JSON from LLM response
            llm_text = result.get('response', '')
            # Try to parse JSON from the response
            try:
                # Find JSON in the response (LLMs might add extra text)
                start = llm_text.find('{')
                end = llm_text.rfind('}') + 1
                if start >= 0 and end > start:
                    json_str = llm_text[start:end]
                    enrich_data = json.loads(json_str)
                else:
                    raise ValueError('No JSON found in response')
            except:
                # Fallback enrichment if JSON parsing fails
                enrich_data = {
                    'video_id': vid,
                    'source_url': url,
                    'abstract_120w': f'Enrichment failed to parse. Raw transcript length: {len(transcript)} chars.',
                    'key_insights': ['LLM enrichment completed'],
                    'claims': [],
                    'entities': [],
                    'action_items': ['Review enrichment output'],
                    'confidence': 'low',
                    'doctrine_map': {
                        'principles': ['Local-first'],
                        'themes': ['Automation']
                    },
                    'provenance': {
                        'ingested_at': datetime.now().isoformat(),
                        'initiator': 'DIGITAL LABOUR Pipeline'
                    }
                }
        else:
            raise Exception(f'LLM API error: {response.status_code}')

    except Exception as e:
        print(f'Warning: LLM enrichment failed ({e}), using fallback')
        enrich_data = {
            'video_id': vid,
            'source_url': url,
            'abstract_120w': f'Local LLM enrichment failed. Transcript length: {len(transcript)} chars.',
            'key_insights': ['Transcript ingested successfully'],
            'claims': [],
            'entities': [],
            'action_items': ['Review LLM configuration'],
            'confidence': 'low',
            'doctrine_map': {
                'principles': ['Local-first', 'Resilience'],
                'themes': ['Second Brain', 'Knowledge Management']
            },
            'provenance': {
                'ingested_at': datetime.now().isoformat(),
                'initiator': 'DIGITAL LABOUR Pipeline'
            }
        }

    # Write enrichment files
    with open(base_dir / 'enrich.json', 'w') as f:
        json.dump(enrich_data, f, indent=2)

    with open(base_dir / 'enrich.md', 'w') as f:
        f.write(f'# {vid} - Second Brain Enrichment\n\n')
        f.write(f'**Abstract:** {enrich_data.get("abstract_120w", "")}\n\n')
        if enrich_data.get('key_insights'):
            f.write('**Key Insights:**\n')
            for insight in enrich_data['key_insights']:
                f.write(f'- {insight}\n')
            f.write('\n')
        if enrich_data.get('action_items'):
            f.write('**Action Items:**\n')
            for action in enrich_data['action_items']:
                f.write(f'- {action}\n')
            f.write('\n')
        f.write(
            f'**Confidence:** {enrich_data.get("confidence", "unknown")}\n')
        f.write(f'**Processed:** {enrich_data["provenance"]["ingested_at"]}\n')

    print('✓ Enrichment complete')

if __name__ == '__main__':
    main()
