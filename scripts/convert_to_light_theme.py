#!/usr/bin/env python3
"""
Automated Light Theme Conversion Script
Converts dark theme references to light theme across all TypeScript/TSX files
"""

import os
import re
from pathlib import Path

# Color mapping dictionary
COLOR_MAPPINGS = {
    # Text colors
    'text-white': 'text-gray-900',
    'text-white/50': 'text-gray-600',
    'text-white/40': 'text-gray-700',
    'text-white/30': 'text-gray-700',
    'text-white/25': 'text-gray-500',
    'text-white/20': 'text-gray-500',
    'text-white/10': 'text-gray-400',
    
    # Background colors
    'bg-cosmic': 'bg-white',
    'bg-\\[#0D1829\\]': 'bg-gray-100',
    'bg-\\[#0a0a0f\\]': 'bg-white',
    
    # Border colors
    'border-white/10': 'border-gray-300',
    'border-white/20': 'border-gray-300',
    'border-white/15': 'border-gray-300',
    'border-white/5': 'border-gray-200',
    'border-white/30': 'border-gray-400',
    
    # Hover/Interactive states
    'hover:border-white': 'hover:border-gray-400',
    'hover:text-white': 'hover:text-gray-900',
    'hover:bg-white/5': 'hover:bg-gray-50',
    
    # Subtle backgrounds
    'bg-white/\\[0.02\\]': 'bg-gray-50',
    'bg-white/\\[0.015\\]': 'bg-gray-50',
    'bg-white/5': 'bg-blue-50',
}

def convert_file(file_path):
    """Convert a single file from dark to light theme"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Apply all color mappings
        for dark, light in COLOR_MAPPINGS.items():
            # Use word boundaries to avoid partial replacements
            pattern = rf'\b{re.escape(dark)}\b'
            content = re.sub(pattern, light, content)
        
        # Only write if changes were made
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Main conversion function"""
    import os
    # Get the script's directory and navigate to frontend
    script_dir = Path(__file__).parent.parent
    frontend_path = script_dir / 'frontend' / 'frontend' / 'src'
    
    if not frontend_path.exists():
        print(f"Frontend path not found: {frontend_path}")
        return
    
    tsx_files = list(frontend_path.glob('**/*.tsx')) + list(frontend_path.glob('**/*.ts'))
    
    converted_count = 0
    total_count = len(tsx_files)
    
    print(f"Found {total_count} TypeScript/TSX files")
    print("Converting to light theme...")
    print("-" * 50)
    
    for file_path in tsx_files:
        if convert_file(file_path):
            print(f"✓ {file_path.relative_to(frontend_path)}")
            converted_count += 1
    
    print("-" * 50)
    print(f"Conversion complete: {converted_count}/{total_count} files updated")

if __name__ == '__main__':
    main()
