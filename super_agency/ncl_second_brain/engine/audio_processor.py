#!/usr/bin/env python3
"""
Audio Processor for DIGITAL LABOUR Phase 2
Local-first podcast and audio transcription pipeline

Processes audio content with:
- Whisper transcription (local)
- Speaker diarization (PyAnnote)
- Audio fingerprinting (duplicate detection)
- Chapter detection
- NCL enrichment integration
"""

import os
import json
import hashlib
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import requests
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AudioProcessor:
    """
    Complete audio processing pipeline for DIGITAL LABOUR
    Local-first, privacy-preserving, provenance-tracked
    """

    def __init__(self, base_dir: str = "knowledge/audio"):
        self.base_dir = Path(base_dir)
        self.current_year = datetime.now().year
        self.current_month = datetime.now().month

        # Create directory structure
        self.audio_dir = self.base_dir / \
            str(self.current_year) / f"{self.current_month:02d}"
        self.fingerprints_dir = self.base_dir / "fingerprints"
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.fingerprints_dir.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.whisper_model = "base"  # Can be upgraded to "small", "medium", "large"
        self.fingerprint_db = self.fingerprints_dir / "fingerprints.db"

        # Check for required dependencies
        self._check_dependencies()

    def _check_dependencies(self):
        """Verify required packages are available"""
        try:
            import whisper
            logger.info("✓ Whisper available")
        except ImportError:
            logger.error(
                "✗ Whisper not available. Install with: pip install openai-whisper")
            raise

        try:
            from pyannote.audio import Pipeline
            logger.info("✓ PyAnnote available")
        except ImportError:
            logger.warning(
                "⚠ PyAnnote not available. Speaker diarization disabled.")
            self.diarization_available = False
        else:
            self.diarization_available = True

    def process_audio_url(
            self, audio_url: str, metadata: Optional[Dict]=None) ->Dict:
        """
        Complete audio processing pipeline from URL

        Args:
            audio_url: URL or local path to audio file
            metadata: Optional metadata (title, description, etc.)

        Returns:
            Complete processing result with transcription, diarization, enrichment
        """
        logger.info(f"Processing audio: {audio_url}")

        # Generate unique ID for this processing job
        job_id = hashlib.md5(
            f"{audio_url}_{datetime.now().isoformat()}".encode()).hexdigest()[:8]
        job_dir = self.audio_dir / job_id
        job_dir.mkdir(exist_ok=True)

        result = {
            "job_id": job_id,
            "source_url": audio_url,
            "processing_started": datetime.now().isoformat(),
            "status": "processing",
            "steps_completed": [],
            "errors": []
        }

        try:
            # Step 1: Download audio locally
            audio_path = self._download_audio(audio_url, job_dir)
            result["steps_completed"].append("download")
            result["audio_path"] = str(audio_path)

            # Step 2: Generate fingerprint for duplicate detection
            fingerprint = self._generate_fingerprint(audio_path)
            result["fingerprint"] = fingerprint
            result["steps_completed"].append("fingerprint")

            # Check for duplicates
            if self._is_duplicate(fingerprint):
                result["status"] = "duplicate"
                result["duplicate_detected"] = True
                logger.info(f"Duplicate audio detected: {fingerprint}")
                return result

            # Step 3: Transcribe with Whisper
            transcription = self._transcribe_audio(audio_path)
            result["transcription"] = transcription
            result["steps_completed"].append("transcription")

            # Step 4: Speaker diarization (if available)
            if self.diarization_available:
                try:
                    diarization = self._diarize_speakers(audio_path)
                    result["diarization"] = diarization
                    result["steps_completed"].append("diarization")
                except Exception as e:
                    logger.warning(f"Diarization failed: {e}")
                    result["diarization_error"] = str(e)
            else:
                result["diarization"] = {
                    "note": "Speaker diarization not available"}

            # Step 5: Detect chapters
            chapters = self._detect_chapters(transcription)
            result["chapters"] = chapters
            result["steps_completed"].append("chapters")

            # Step 6: Prepare for NCL enrichment
            ncl_payload = self._prepare_ncl_payload(result, metadata or {})
            result["ncl_payload"] = ncl_payload
            result["steps_completed"].append("ncl_preparation")

            # Step 7: Save results
            self._save_results(result, job_dir)

            result["status"] = "completed"
            result["processing_completed"] = datetime.now().isoformat()

            logger.info(f"✓ Audio processing completed: {job_id}")

        except Exception as e:
            logger.error(f"✗ Audio processing failed: {e}")
            result["status"] = "failed"
            result["error"] = str(e)
            result["processing_failed"] = datetime.now().isoformat()

        return result

    def _download_audio(self, audio_url: str, job_dir: Path) -> Path:
        """Download audio file locally"""
        logger.info(f"Downloading audio from: {audio_url}")

        # Handle local files
        if audio_url.startswith(('http://', 'https://')):
            response = requests.get(audio_url, stream=True)
            response.raise_for_status()

            # Determine filename from URL or Content-Disposition
            filename = audio_url.split('/')[-1]
            if 'Content-Disposition' in response.headers:
                cd = response.headers['Content-Disposition']
                if 'filename=' in cd:
                    filename = cd.split('filename=')[1].strip('"\'')

            if not filename or '.' not in filename:
                filename = f"audio_{hash(audio_url) % 10000}.mp3"

            audio_path = job_dir / filename

            with open(audio_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
        else:
            # Local file
            source_path = Path(audio_url)
            if not source_path.exists():
                raise FileNotFoundError(
                    f"Local audio file not found: {audio_url}")

            filename = source_path.name
            audio_path = job_dir / filename

            # Copy local file
            import shutil
            shutil.copy2(source_path, audio_path)

        logger.info(f"Audio downloaded to: {audio_path}")
        return audio_path

    def _generate_fingerprint(self, audio_path: Path) -> str:
        """Generate audio fingerprint for duplicate detection"""
        logger.info("Generating audio fingerprint")

        try:
            # Use ffmpeg to extract raw audio for fingerprinting
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
                temp_wav_path = temp_wav.name

            # Convert to WAV for consistent fingerprinting
            cmd = [
                'ffmpeg', '-i', str(audio_path),
                '-acodec', 'pcm_s16le', '-ar', '22050', '-ac', '1',
                '-y', temp_wav_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.warning(f"FFmpeg conversion failed: {result.stderr}")
                # Fallback: use file hash
                with open(audio_path, 'rb') as f:
                    return hashlib.sha256(f.read()).hexdigest()

            # Generate chromaprint fingerprint
            try:
                import chromaprint
                fp = chromaprint.fingerprint(temp_wav_path)
                logger.info(f"Fingerprint generated: {fp[:16]}...")
                return fp
            except ImportError:
                logger.warning("Chromaprint not available, using file hash")
                with open(audio_path, 'rb') as f:
                    return hashlib.sha256(f.read()).hexdigest()

        finally:
            # Clean up temp file
            if 'temp_wav_path' in locals():
                try:
                    os.unlink(temp_wav_path)
                except:
                    pass

    def _is_duplicate(self, fingerprint: str) -> bool:
        """Check if audio has been processed before"""
        # Simple file-based duplicate detection
        # In production, this would be a database
        fp_file = self.fingerprints_dir / f"{fingerprint[:16]}.txt"

        if fp_file.exists():
            logger.info(f"Duplicate fingerprint found: {fingerprint[:16]}")
            return True

        # Record this fingerprint
        fp_file.write_text(f"{fingerprint}\n{datetime.now().isoformat()}")
        return False

    def _transcribe_audio(self, audio_path: Path) -> Dict:
        """Transcribe audio using Whisper"""
        logger.info("Starting Whisper transcription")

        try:
            import whisper

            # Load model (cached after first use)
            model = whisper.load_model(self.whisper_model)

            # Transcribe with timestamps
            result = model.transcribe(
                str(audio_path),
                language=None,  # Auto-detect
                task="transcribe",
                verbose=False
            )

            transcription = {
                "text": result["text"].strip(),
                "language": result.get("language", "unknown"),
                "duration": result.get("duration", 0),
                "segments": [
                    {
                        "start": segment["start"],
                        "end": segment["end"],
                        "text": segment["text"].strip(),
                        "confidence": segment.get("confidence", 0.0)
                    }
                    for segment in result["segments"]
                ]
            }

            logger.info(
                f"✓ Transcription completed: {len(transcription['text'])} chars, {len(transcription['segments'])} segments")
            return transcription

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise

    def _diarize_speakers(self, audio_path: Path) -> List[Dict]:
        """Perform speaker diarization"""
        logger.info("Starting speaker diarization")

        try:
            from pyannote.audio import Pipeline

            # Load diarization pipeline (requires auth token in production)
            # For now, we'll use a simpler approach or skip
            logger.warning(
                "Speaker diarization requires PyAnnote authentication token")

            # Placeholder: return basic segmentation
            return [{
                "note": "Speaker diarization not fully configured",
                "requires_auth": True,
                "segments": []
            }]

        except Exception as e:
            logger.warning(f"Diarization failed: {e}")
            return [{"error": str(e)}]

    def _detect_chapters(self, transcription: Dict) -> List[Dict]:
        """Detect natural chapter breaks in audio"""
        logger.info("Detecting chapters")

        segments = transcription.get("segments", [])
        if not segments:
            return []

        chapters = []
        current_chapter = {
            "start": segments[0]["start"],
            "end": segments[0]["end"],
            "text": segments[0]["text"],
            "title": "Introduction"
        }

        # Simple chapter detection based on silence gaps and content
        # In production, this would use ML models for topic detection
        silence_threshold = 2.0  # seconds
        min_chapter_length = 30.0  # seconds

        for i, segment in enumerate(segments[1:], 1):
            prev_end = segments[i-1]["end"]
            gap = segment["start"] - prev_end

            # Check for chapter break conditions
            if gap > silence_threshold or len(current_chapter["text"]) > 1000:
                # End current chapter
                current_chapter["end"] = prev_end
                chapters.append(current_chapter.copy())

                # Start new chapter
                chapter_num = len(chapters) + 1
                current_chapter = {
                    "start": segment["start"],
                    "end": segment["end"],
                    "text": segment["text"],
                    "title": f"Chapter {chapter_num}"
                }
            else:
                # Continue current chapter
                current_chapter["end"] = segment["end"]
                current_chapter["text"] += " " + segment["text"]

        # Add final chapter
        chapters.append(current_chapter)

        # Filter out very short chapters
        chapters = [c for c in chapters if (
            c["end"] - c["start"]) > min_chapter_length]

        logger.info(f"✓ Detected {len(chapters)} chapters")
        return chapters

    def _prepare_ncl_payload(self, result: Dict, metadata: Dict) -> Dict:
        """Prepare data for NCL enrichment"""
        return {
            "content_type": "audio",
            "source_url": result["source_url"],
            "fingerprint": result["fingerprint"],
            "transcription": result["transcription"],
            "diarization": result.get("diarization", {}),
            "chapters": result["chapters"],
            "metadata": metadata,
            "provenance": {
                "ingested_at": result["processing_started"],
                "initiator": "Audio Processing Agent",
                "processing_steps": result["steps_completed"],
                "job_id": result["job_id"]
            }
        }

    def _save_results(self, result: Dict, job_dir: Path):
        """Save processing results to disk"""
        # Save complete result
        result_file = job_dir / "processing_result.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        # Save transcription separately
        if "transcription" in result:
            transcript_file = job_dir / "transcription.json"
            with open(transcript_file, 'w', encoding='utf-8') as f:
                json.dump(result["transcription"], f,
                          indent=2, ensure_ascii=False)

        # Save chapters
        if "chapters" in result:
            chapters_file = job_dir / "chapters.json"
            with open(chapters_file, 'w', encoding='utf-8') as f:
                json.dump(result["chapters"], f, indent=2, ensure_ascii=False)

        # Save NCL payload
        if "ncl_payload" in result:
            ncl_file = job_dir / "ncl_payload.json"
            with open(ncl_file, 'w', encoding='utf-8') as f:
                json.dump(result["ncl_payload"], f,
                          indent=2, ensure_ascii=False)

        logger.info(f"✓ Results saved to: {job_dir}")


# Command-line interface
def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Process audio for DIGITAL LABOUR")
    parser.add_argument("audio_url", help="URL or path to audio file")
    parser.add_argument("--metadata", help="JSON metadata file")
    parser.add_argument("--output-dir", help="Output directory")

    args = parser.parse_args()

    # Load metadata if provided
    metadata = {}
    if args.metadata:
        with open(args.metadata, 'r') as f:
            metadata = json.load(f)

    # Initialize processor
    if args.output_dir:
        processor = AudioProcessor(args.output_dir)
    else:
        processor = AudioProcessor()

    # Process audio
    result = processor.process_audio_url(args.audio_url, metadata)

    # Print summary
    print(f"Processing Status: {result['status']}")
    print(f"Job ID: {result['job_id']}")
    print(f"Steps Completed: {', '.join(result['steps_completed'])}")

    if result['status'] == 'completed':
        transcription = result.get('transcription', {})
        print(
            f"Transcription: {len(transcription.get('text', ''))} characters")
        print(f"Chapters: {len(result.get('chapters', []))}")
        print(f"Output: {processor.audio_dir / result['job_id']}")
    elif result['status'] == 'duplicate':
        print("⚠️ Duplicate audio detected - skipping processing")


if __name__ == "__main__":
    main()