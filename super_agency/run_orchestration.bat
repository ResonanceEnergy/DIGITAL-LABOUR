@echo off
cd /d "C:\Dev\SuperAgency-Shared"
python -c "import asyncio; from conductor_agent import ConductorAgent; asyncio.run(ConductorAgent().orchestrate_cycle())"
