#!/usr/bin/env python3
"""Check Pinecone index status"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from pinecone import Pinecone

pc = Pinecone(api_key=os.environ['PINECONE_API_KEY'])

print("📊 Checking Pinecone indexes status...\n")

indexes = pc.list_indexes()
if not indexes:
    print("❌ No indexes found!")
else:
    for idx in indexes:
        print(f"Index: {idx.name}")
        print(f"  Status: {idx.status.state}")
        print(f"  Ready: {idx.status.ready}")
        print(f"  Dimension: {idx.dimension}")
        print(f"  Metric: {idx.metric}")
        print()
