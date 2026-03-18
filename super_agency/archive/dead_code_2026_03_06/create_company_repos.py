#!/usr/bin/env python3
"""
BIT RAGE LABOUR Company Repository Creator
Creates separate repositories for all companies in the NCC Doctrine portfolio
"""

import json
import os
from pathlib import Path

def create_company_repositories():
    """Create separate repositories for all companies in the portfolio"""

    # Load portfolio data
    with open('portfolio.json', 'r') as f:
        portfolio = json.load(f)

    companies = portfolio['repositories']

    # Create companies directory if it doesn't exist
    companies_dir = Path('companies')
    companies_dir.mkdir(exist_ok=True)

    print('=== CREATING SEPARATE REPOSITORIES FOR ALL COMPANIES ===')
    print(f'Found {len(companies)} companies in portfolio\n')

    for repo_data in companies:
        company_name = repo_data['name']
        visibility = repo_data['visibility']
        tier = repo_data['tier']
        autonomy_level = repo_data['autonomy_level']
        risk_tier = repo_data['risk_tier']

        # Create company directory
        company_dir = companies_dir / company_name
        company_dir.mkdir(exist_ok=True)

        # Create basic repository structure
        (company_dir / 'src').mkdir(exist_ok=True)
        (company_dir / 'docs').mkdir(exist_ok=True)
        (company_dir / 'tests').mkdir(exist_ok=True)
        (company_dir / 'config').mkdir(exist_ok=True)

        # Create README.md
        readme_content = f'''# {company_name}

**Company Repository** - BIT RAGE LABOUR Portfolio Company

## Overview

{company_name} is a portfolio company within the BIT RAGE LABOUR ecosystem.

## Repository Information

- **Visibility**: {visibility}
- **Tier**: {tier}
- **Autonomy Level**: {autonomy_level}
- **Risk Tier**: {risk_tier}
- **Created**: February 20, 2026
- **Parent Organization**: BIT RAGE LABOUR

## Directory Structure

```
{company_name}/
├── src/                 # Source code
├── docs/                # Documentation
├── tests/               # Test files
├── config/              # Configuration files
└── README.md           # This file
```

## Integration Status

This repository is part of the BIT RAGE LABOUR NCC-Doctrine integration framework.

## Contact

For questions about this company repository, contact the BIT RAGE LABOUR executive team.
'''

        with open(company_dir / 'README.md', 'w', encoding='utf-8') as f:
            f.write(readme_content)

        # Create .gitignore
        gitignore_content = '''# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# C extensions
*.so

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# PyInstaller
*.manifest
*.spec

# Installer logs
pip-log.txt
pip-delete-this-directory.txt

# Unit test / coverage reports
htmlcov/
.tox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
.hypothesis/
.pytest_cache/

# Virtual environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# OS generated files
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Logs
*.log
logs/

# Temporary files
*.tmp
*.temp
'''

        with open(company_dir / '.gitignore', 'w', encoding='utf-8') as f:
            f.write(gitignore_content)

        # Create basic __init__.py if it's a Python project
        with open(company_dir / 'src' / '__init__.py', 'w', encoding='utf-8') as f:
            f.write(f'''"""BIT RAGE LABOUR Portfolio Company: {company_name}"""

__version__ = "1.0.0"
__author__ = "BIT RAGE LABOUR"
__description__ = "{company_name} portfolio company"
''')

        print(f'✓ Created repository: {company_name}')

    print(f'\n🎯 SUCCESS: Created {len(companies)} company repositories under companies/ directory')
    print('Each repository includes:')
    print('  - Basic directory structure (src/, docs/, tests/, config/)')
    print('  - README.md with company information')
    print('  - .gitignore for Python projects')
    print('  - Basic __init__.py in src/')

    # Create master companies index
    create_companies_index(companies)

def create_companies_index(companies):
    """Create a master index of all company repositories"""

    index_content = '''# BIT RAGE LABOUR Companies Index

**Master Index of All Portfolio Companies**

Generated: February 20, 2026
Total Companies: {len}

## Company Repositories

| Company Name | Visibility | Tier | Autonomy | Risk Tier |
|-------------|------------|------|----------|-----------|
{rows}

## Directory Structure

```
companies/
├── Company1/
│   ├── src/
│   ├── docs/
│   ├── tests/
│   ├── config/
│   ├── README.md
│   └── .gitignore
├── Company2/
│   └── ...
└── README.md (this file)
```

## Integration Status

All company repositories are part of the BIT RAGE LABOUR NCC-Doctrine integration framework and are ready for development.

## Next Steps

1. Initialize git repositories for each company
2. Set up CI/CD pipelines
3. Configure access controls based on visibility settings
4. Begin development work on individual companies

## Contact

BIT RAGE LABOUR Executive Team
'''

    rows = []
    for repo in companies:
        rows.append(f'| {repo["name"]} | {repo["visibility"]} | {repo["tier"]} | {repo["autonomy_level"]} | {repo["risk_tier"]} |')

    index_content = index_content.format(len=len(companies), rows='\n'.join(rows))

    with open('companies/README.md', 'w', encoding='utf-8') as f:
        f.write(index_content)

    print('✓ Created companies/README.md master index')

if __name__ == '__main__':
    create_company_repositories()