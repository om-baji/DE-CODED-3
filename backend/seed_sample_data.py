#!/usr/bin/env python3
"""
Script to seed sample data for testing the RAG Agent 3 system
Creates sample complaint and proof images
"""
import os
import sys
from pathlib import Path
import asyncio
from PIL import Image, ImageDraw, ImageFont
import io
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from verification_pipeline import verification_pipeline

def create_sample_image(text: str, color: tuple = (200, 200, 200)) -> bytes:
    """Create a sample image with text"""
    # Create a 800x600 image
    img = Image.new('RGB', (800, 600), color=color)
    draw = ImageDraw.Draw(img)
    
    # Add text
    try:
        # Try to use a nice font
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
    except:
        font = ImageFont.load_default()
    
    # Get text bounding box
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Center text
    position = ((800 - text_width) // 2, (600 - text_height) // 2)
    draw.text(position, text, fill=(50, 50, 50), font=font)
    
    # Add timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    draw.text((20, 20), timestamp, fill=(100, 100, 100))
    
    # Convert to bytes
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=85)
    return buffer.getvalue()

async def seed_data():
    """Seed sample complaint and proof data"""
    print("🌱 Seeding sample data...")
    
    # Sample 1: Waste Collection - VERIFIED scenario
    print("\n1️⃣ Creating Sample 1: Waste Collection (Should VERIFY)")
    
    complaint_1_image = create_sample_image(
        "BEFORE:\nWaste Pile\nGarbage Accumulated",
        color=(180, 140, 140)  # Brownish - dirty
    )
    
    proof_1_image = create_sample_image(
        "AFTER:\nArea Cleaned\nWaste Removed",
        color=(150, 200, 150)  # Greenish - clean
    )
    
    complaint_1_id = "COMP-SAMPLE-001"
    lat1, lon1 = 37.7749, -122.4194  # San Francisco
    
    result1_complaint = await verification_pipeline.ingest_complaint(
        complaint_id=complaint_1_id,
        image_bytes=complaint_1_image,
        lat=lat1,
        lon=lon1,
        ts_iso="2025-08-08T10:00:00Z",
        metadata={'issue_type': 'waste_collection'}
    )
    print(f"   ✅ Complaint ingested: {result1_complaint}")
    
    proof_1_id = "PROOF-SAMPLE-001"
    result1_proof = await verification_pipeline.ingest_proof(
        proof_id=proof_1_id,
        complaint_id=complaint_1_id,
        worker_id="WORKER-001",
        image_bytes=proof_1_image,
        lat=lat1 + 0.0001,  # ~11m away
        lon=lon1 + 0.0001,
        ts_iso="2025-08-08T11:30:00Z"
    )
    print(f"   ✅ Proof ingested: {result1_proof}")
    
    print(f"   ⏳ Waiting 5 seconds for Pinecone indexing...")
    await asyncio.sleep(5)
    
    print(f"   🔍 Running verification for {proof_1_id}...")
    verification1 = await verification_pipeline.verify_proof(proof_1_id)
    print(f"   📊 Result: {verification1['verification_status']}")
    print(f"   📈 Score: {verification1['scoring']['composite_score']:.2f}")
    
    # Sample 2: Drainage - QUESTIONABLE scenario (moderate distance)
    print("\n2️⃣ Creating Sample 2: Drainage (Should be QUESTIONABLE)")
    
    complaint_2_image = create_sample_image(
        "BEFORE:\nBlocked Drain\nWater Stagnant",
        color=(140, 160, 180)  # Bluish - water
    )
    
    proof_2_image = create_sample_image(
        "AFTER:\nDrain Partially Clear\nSome Water Flow",
        color=(160, 180, 180)  # Lighter blue
    )
    
    complaint_2_id = "COMP-SAMPLE-002"
    lat2, lon2 = 37.7750, -122.4200
    
    result2_complaint = await verification_pipeline.ingest_complaint(
        complaint_id=complaint_2_id,
        image_bytes=complaint_2_image,
        lat=lat2,
        lon=lon2,
        ts_iso="2025-08-08T09:00:00Z",
        metadata={'issue_type': 'drainage'}
    )
    print(f"   ✅ Complaint ingested: {result2_complaint}")
    
    proof_2_id = "PROOF-SAMPLE-002"
    result2_proof = await verification_pipeline.ingest_proof(
        proof_id=proof_2_id,
        complaint_id=complaint_2_id,
        worker_id="WORKER-002",
        image_bytes=proof_2_image,
        lat=lat2 + 0.0003,  # ~33m away (borderline)
        lon=lon2 + 0.0003,
        ts_iso="2025-08-08T10:30:00Z"
    )
    print(f"   ✅ Proof ingested: {result2_proof}")
    
    print(f"   🔍 Running verification for {proof_2_id}...")
    verification2 = await verification_pipeline.verify_proof(proof_2_id)
    print(f"   📊 Result: {verification2['verification_status']}")
    print(f"   📈 Score: {verification2['scoring']['composite_score']:.2f}")
    
    # Sample 3: Infrastructure - REJECTED scenario (wrong location)
    print("\n3️⃣ Creating Sample 3: Infrastructure (Should REJECT - wrong location)")
    
    complaint_3_image = create_sample_image(
        "BEFORE:\nPothole\nRoad Damage",
        color=(160, 160, 160)  # Gray - road
    )
    
    proof_3_image = create_sample_image(
        "AFTER:\nRoad Repaired\nSmooth Surface",
        color=(180, 180, 180)  # Lighter gray
    )
    
    complaint_3_id = "COMP-SAMPLE-003"
    lat3, lon3 = 37.7760, -122.4210
    
    result3_complaint = await verification_pipeline.ingest_complaint(
        complaint_id=complaint_3_id,
        image_bytes=complaint_3_image,
        lat=lat3,
        lon=lon3,
        ts_iso="2025-08-08T08:00:00Z",
        metadata={'issue_type': 'infrastructure_repair'}
    )
    print(f"   ✅ Complaint ingested: {result3_complaint}")
    
    proof_3_id = "PROOF-SAMPLE-003"
    result3_proof = await verification_pipeline.ingest_proof(
        proof_id=proof_3_id,
        complaint_id=complaint_3_id,
        worker_id="WORKER-003",
        image_bytes=proof_3_image,
        lat=lat3 + 0.001,  # ~111m away (too far!)
        lon=lon3 + 0.001,
        ts_iso="2025-08-08T09:30:00Z"
    )
    print(f"   ✅ Proof ingested: {result3_proof}")
    
    print(f"   🔍 Running verification for {proof_3_id}...")
    verification3 = await verification_pipeline.verify_proof(proof_3_id)
    print(f"   📊 Result: {verification3['verification_status']}")
    print(f"   📈 Score: {verification3['scoring']['composite_score']:.2f}")
    
    print("\n✅ Sample data seeding complete!")
    print(f"\n📝 Summary:")
    print(f"   - Sample 1: {verification1['verification_status']} (Score: {verification1['scoring']['composite_score']:.2f})")
    print(f"   - Sample 2: {verification2['verification_status']} (Score: {verification2['scoring']['composite_score']:.2f})")
    print(f"   - Sample 3: {verification3['verification_status']} (Score: {verification3['scoring']['composite_score']:.2f})")

if __name__ == "__main__":
    asyncio.run(seed_data())
