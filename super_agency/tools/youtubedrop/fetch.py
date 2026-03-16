#!/usr/bin/env python3
"""
YouTube Drop Fetcher - Production Implementation

Fetches transcripts using youtube-transcript-api for automatic captions.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from typing import List, Dict, Any

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api.formatters import TextFormatter, WebVTTFormatter
    YOUTUBE_TRANSCRIPT_API_AVAILABLE = True
except ImportError:
    print("Warning: youtube-transcript-api not available. Install with: pip install youtube-transcript-api")
    YOUTUBE_TRANSCRIPT_API_AVAILABLE = False

def extract_video_id(url: str) -> str:
    """Extract YouTube video ID from URL"""
    parsed = urlparse(url)
    if parsed.hostname in ['youtu.be']:
        return parsed.path.lstrip('/')
    if parsed.hostname in ['www.youtube.com', 'youtube.com']:
        query = parse_qs(parsed.query)
        return query.get('v', [None])[0]
    return None

def fetch_transcript(video_id: str, output_dir: Path) -> bool:
    """
    Fetch transcript for video_id and save to output_dir

    Uses youtube-transcript-api to get automatic captions.
    Falls back to manual transcript if available.
    """

    if not YOUTUBE_TRANSCRIPT_API_AVAILABLE:
        print(
            f"ERROR: youtube-transcript-api not available for video {video_id}")
        print("Install with: pip install youtube-transcript-api")
        return False

    print(f"Fetching transcript for video {video_id}...")

    try:
        # Try to get transcript with automatic captions first
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        # Prefer manual transcript, fall back to auto-generated
        transcript = None
        try:
            transcript = transcript_list.find_manually_created_transcript([
                                                                          'en'])
        except:
            try:
                transcript = transcript_list.find_generated_transcript(['en'])
            except:
                print(f"No English transcript available for {video_id}")
                return False

        # Fetch the actual transcript data
        transcript_data = transcript.fetch()

        if not transcript_data:
            print(f"Empty transcript for {video_id}")
            return False

        # Convert to different formats
        text_formatter = TextFormatter()
        vtt_formatter = WebVTTFormatter()

        # Plain text
        raw_text = text_formatter.format_transcript(transcript_data)

        # WebVTT format
        vtt_content = vtt_formatter.format_transcript(transcript_data)

        # Segments with timestamps
        segments = [
            {
                "start": entry['start'],
                "end": entry['start'] + entry['duration'],
                "text": entry['text']
            }
            for entry in transcript_data
        ]

        # Write outputs
        (output_dir / "raw.txt").write_text(raw_text, encoding='utf-8')
        (output_dir / "raw.vtt").write_text(vtt_content, encoding='utf-8')
        (output_dir / "segments.json").write_text(
            json.dumps(segments, indent=2),
            encoding='utf-8'
        )

        print(
            f"Successfully fetched transcript: {len(raw_text)} characters, {len(segments)} segments")
        return True

    except Exception as e:
        print(f"ERROR fetching transcript for {video_id}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Fetch YouTube transcript")
    parser.add_argument("url", help="YouTube URL")
    parser.add_argument("--out", "-o", required=True,
                       help="Output directory")
    parser.add_argument("--format", choices=['vtt', 'txt', 'both'],
                       default='both', help="Output format")

    args = parser.parse_args()

    video_id = extract_video_id(args.url)
    if not video_id:
        print(f"ERROR: Could not extract video ID from {args.url}")
        sys.exit(1)

    output_dir = Path(args.out)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Processing video: {video_id}")
    print(f"Output directory: {output_dir}")

    if fetch_transcript(video_id, output_dir):
        print("✓ Transcript fetched successfully")
        sys.exit(0)
    else:
        print("✗ Failed to fetch transcript")
        sys.exit(1)

if __name__ == "__main__":
    main()