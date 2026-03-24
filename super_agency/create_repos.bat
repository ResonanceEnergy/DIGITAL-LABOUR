@echo off
setlocal enabledelayedexpansion

cd repos

set repos=NATEBJONES ADVENTUREHEROAUTO Crimson-Compass CIVIL-FORGE-TECHNOLOGIES- GEET-PLASMA-PROJECT TESLA-TECH ELECTRIC-UNIVERSE VORTEX-HUNTER MircoHydro electric-ice SUPERSTONK-TRADER HUMAN-HEALTH Adventure-Hero-Chronicles-Of-Glory QDFG1 NCC-Doctrine NCC resonance-uy-py perpetual-flow-cube

for %%r in (%repos%) do (
    if not exist "%%r" (
        echo Creating %%r...
        mkdir "%%r"
        cd "%%r"
        git init >nul 2>&1
        echo # %%r> README.md
        echo.>> README.md
        echo ## Bit Rage Systems Repository>> README.md
        echo.>> README.md
        echo **Status**: Initialization Phase>> README.md
        git add . >nul 2>&1
        git commit -m "Initial commit - Bit Rage Systems repo initialization" >nul 2>&1
        cd ..
        echo ✓ Created %%r
    ) else (
        echo - %%r already exists
    )
)

echo.
echo Repo creation complete!
echo Total repos created: %repos_count%