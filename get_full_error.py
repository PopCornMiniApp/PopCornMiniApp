#!/usr/bin/env python3
"""Get full error message from HuggingFace Space"""

import os
from dotenv import load_dotenv
from huggingface_hub import HfApi

load_dotenv()

token = os.getenv('HF_TOKEN')
space_name = os.getenv('HF_SPACE_NAME', 'ToolKit-backend/PopCorn')

api = HfApi(token=token)
space_info = api.space_info(space_name)

if space_info.runtime and hasattr(space_info.runtime, 'raw'):
    error_msg = space_info.runtime.raw.get('errorMessage', 'No error message')
    print("="*80)
    print("FULL ERROR MESSAGE:")
    print("="*80)
    print(error_msg)
    print("="*80)

# Made with Bob
