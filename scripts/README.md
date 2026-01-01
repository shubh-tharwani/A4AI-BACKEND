# Scripts Directory

This directory contains utility scripts for development, testing, and maintenance of the AI for Education platform.

## Available Scripts

### Development Scripts

**`start_local.py`**
- Starts the local development server with proper configuration
- Usage: `python scripts/start_local.py`

### Testing Scripts

**`test_*.py`**
- Various testing scripts for different platform components
- `test_audio_generation.py` - Tests speech synthesis
- `test_story_generation.py` - Tests content generation
- `test_image_gen.py` - Tests visual aid generation
- `test_regional_story.py` - Tests localized content

### Data Management Scripts

**`create_firebase_users.py`**
- Creates test user accounts in Firebase
- Usage: `python scripts/create_firebase_users.py`

**`create_test_audio.py`**
- Generates test audio samples
- Usage: `python scripts/create_test_audio.py`

**`download_speech_samples.py`**
- Downloads sample audio files for testing
- Usage: `python scripts/download_speech_samples.py`

### Debugging Scripts

**`debug_planning.py`**
- Debug utility for lesson planning functionality
- Usage: `python scripts/debug_planning.py`

## Running Scripts

### From Project Root
```bash
python scripts/script_name.py
```

### With Virtual Environment
```powershell
# Activate environment first
.venv\Scripts\Activate.ps1

# Then run script
python scripts/script_name.py
```

## Creating New Scripts

When creating utility scripts:

1. Add them to this directory
2. Include a docstring explaining purpose
3. Add command-line argument parsing if needed
4. Update this README with script description
5. Make scripts idempotent when possible

### Script Template
```python
"""
Script Name: example_script.py
Purpose: Brief description of what this script does
Usage: python scripts/example_script.py [options]
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def main():
    parser = argparse.ArgumentParser(description="Script description")
    parser.add_argument("--option", help="Option description")
    args = parser.parse_args()
    
    # Script logic here
    print("Script executed successfully")

if __name__ == "__main__":
    main()
```

## Best Practices

- Keep scripts focused on a single task
- Add error handling and validation
- Print clear progress messages
- Use command-line arguments for flexibility
- Document required environment variables
- Add scripts to .gitignore if they contain secrets

## Common Issues

**Module Not Found Errors**
- Ensure you're running from project root
- Check that virtual environment is activated
- Verify all dependencies are installed

**Credential Errors**
- Verify credentials files are in place
- Check .env file configuration
- Ensure proper permissions on credential files

For more information, refer to the main README.md or open an issue.
