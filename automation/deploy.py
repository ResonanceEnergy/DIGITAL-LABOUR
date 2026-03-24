"""Deploy Script — Packages and deploys the RapidAPI server.

Handles Docker build, spec export, and deployment prep for cloud hosting.

Usage:
    python -m automation.deploy --build          # Build Docker image
    python -m automation.deploy --run             # Run Docker container locally
    python -m automation.deploy --spec            # Export OpenAPI spec
    python -m automation.deploy --fly             # Generate fly.io config
    python -m automation.deploy --railway         # Generate Railway config
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

IMAGE_NAME = "bit-rage-labour-api"
CONTAINER_NAME = "BIT RAGE SYSTEMS-api"


def build_docker():
    """Build the Docker image."""
    print("[DEPLOY] Building Docker image...")
    result = subprocess.run(
        ["docker", "build", "-t", IMAGE_NAME, "."],
        cwd=str(PROJECT_ROOT),
        capture_output=False,
    )
    if result.returncode == 0:
        print(f"[DEPLOY] Image '{IMAGE_NAME}' built successfully")
    else:
        print(f"[DEPLOY] Build failed with code {result.returncode}")
    return result.returncode


def run_docker():
    """Run the API server in a Docker container."""
    print(f"[DEPLOY] Starting container '{CONTAINER_NAME}'...")

    # Stop existing container if running
    subprocess.run(
        ["docker", "rm", "-f", CONTAINER_NAME],
        capture_output=True, check=False,
    )

    result = subprocess.run(
        [
            "docker", "run", "-d",
            "--name", CONTAINER_NAME,
            "-p", "8001:8001",
            "--env-file", ".env",
            IMAGE_NAME,
        ],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        container_id = result.stdout.strip()[:12]
        print(f"[DEPLOY] Container running: {container_id}")
        print(f"[DEPLOY] API available at: http://localhost:8001/docs")
    else:
        print(f"[DEPLOY] Run failed: {result.stderr}")
    return result.returncode


def export_spec():
    """Export OpenAPI spec for RapidAPI upload."""
    output_dir = PROJECT_ROOT / "output"
    output_dir.mkdir(exist_ok=True)
    result = subprocess.run(
        [sys.executable, "-m", "api.rapidapi", "--spec"],
        cwd=str(PROJECT_ROOT),
        capture_output=True, text=True,
    )
    if result.stdout:
        spec_file = output_dir / "rapidapi_openapi.json"
        spec_file.write_text(result.stdout, encoding="utf-8")
        print(f"[DEPLOY] OpenAPI spec saved to {spec_file}")
    else:
        print(f"[DEPLOY] Failed to generate spec: {result.stderr}")


def generate_fly_config():
    """Generate fly.io deployment config."""
    config = """# fly.toml — Fly.io deployment for BIT RAGE SYSTEMS API
app = "bit-rage-labour-api"
primary_region = "yyz"  # Toronto

[build]
  dockerfile = "Dockerfile"

[http_service]
  internal_port = 8001
  force_https = true
  auto_stop_machines = true
  auto_start_machines = true
  min_machines_running = 0

  [http_service.concurrency]
    type = "connections"
    hard_limit = 25
    soft_limit = 20

[[vm]]
  cpu_kind = "shared"
  cpus = 1
  memory_mb = 512
"""
    fly_file = PROJECT_ROOT / "fly.toml"
    fly_file.write_text(config, encoding="utf-8")
    print(f"[DEPLOY] fly.toml created")
    print(f"  Deploy: fly auth login && fly launch && fly deploy")
    print(f"  Set secrets: fly secrets set OPENAI_API_KEY=... STRIPE_API_KEY=...")


def generate_railway_config():
    """Generate Railway deployment config."""
    config = {
        "$schema": "https://railway.app/railway.schema.json",
        "build": {"builder": "DOCKERFILE", "dockerfilePath": "Dockerfile"},
        "deploy": {
            "startCommand": "python -m api.rapidapi --serve --port $PORT",
            "healthcheckPath": "/docs",
            "restartPolicyType": "ON_FAILURE",
        },
    }
    railway_file = PROJECT_ROOT / "railway.json"
    railway_file.write_text(json.dumps(config, indent=2), encoding="utf-8")
    print(f"[DEPLOY] railway.json created")
    print(f"  Deploy: railway login && railway up")
    print(f"  Set env vars in Railway dashboard")


def main():
    parser = argparse.ArgumentParser(description="Deploy RapidAPI Server")
    parser.add_argument("--build", action="store_true", help="Build Docker image")
    parser.add_argument("--run", action="store_true", help="Run Docker container")
    parser.add_argument("--spec", action="store_true", help="Export OpenAPI spec")
    parser.add_argument("--fly", action="store_true", help="Generate fly.io config")
    parser.add_argument("--railway", action="store_true", help="Generate Railway config")
    args = parser.parse_args()

    if args.build:
        build_docker()
    elif args.run:
        build_docker()
        run_docker()
    elif args.spec:
        export_spec()
    elif args.fly:
        generate_fly_config()
    elif args.railway:
        generate_railway_config()
    else:
        # Default: generate all configs
        export_spec()
        generate_fly_config()
        generate_railway_config()
        print(f"\n[DEPLOY] All configs generated. Choose a platform:")
        print(f"  Fly.io:   fly deploy")
        print(f"  Railway:  railway up")
        print(f"  Docker:   python -m automation.deploy --run")


if __name__ == "__main__":
    main()
