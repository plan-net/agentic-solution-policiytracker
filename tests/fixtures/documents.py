"""Test document fixtures for the Political Monitoring Agent."""

import os
import tempfile
from typing import Dict, List


def create_sample_documents(output_dir: str) -> Dict[str, str]:
    """Create sample documents for testing."""
    documents = {}
    
    # Sample markdown document
    md_content = """# EU Digital Services Act Implementation

## Summary
The European Union's Digital Services Act (DSA) introduces new compliance requirements for online platforms and digital services.

## Key Requirements
- Content moderation policies
- Risk assessment procedures
- Transparency reporting
- User notification systems

## Timeline
Implementation deadline: February 2024
Compliance monitoring: Ongoing

## Impact Assessment
This regulation will significantly impact e-commerce platforms operating in the EU market.
"""
    
    md_path = os.path.join(output_dir, "dsa_implementation.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    documents["markdown"] = md_path
    
    # Sample text document
    txt_content = """REGULATORY ALERT: GDPR Update
    
Date: 2024-05-23
Source: European Data Protection Board

New guidance on data processing for AI systems has been released. Companies must ensure compliance with updated privacy requirements.

Key Points:
- Enhanced consent mechanisms required
- Data minimization principles apply
- Regular compliance audits mandatory

Immediate action required for all EU operations.
"""
    
    txt_path = os.path.join(output_dir, "gdpr_alert.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(txt_content)
    documents["text"] = txt_path
    
    # Sample HTML document
    html_content = """<!DOCTYPE html>
<html>
<head>
    <title>Competition Law Update</title>
</head>
<body>
    <h1>German Competition Authority Guidelines</h1>
    
    <p>The Bundeskartellamt has issued new guidelines for digital marketplace regulations.</p>
    
    <h2>Key Changes</h2>
    <ul>
        <li>Market dominance thresholds updated</li>
        <li>Platform responsibility increased</li>
        <li>Cross-border enforcement enhanced</li>
    </ul>
    
    <h2>Implementation</h2>
    <p>Companies operating digital marketplaces in Germany must review their practices within 6 months.</p>
    
    <footer>
        <p>Published: May 2024</p>
    </footer>
</body>
</html>
"""
    
    html_path = os.path.join(output_dir, "competition_update.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    documents["html"] = html_path
    
    # Sample document with low relevance
    low_relevance_content = """Agricultural Weather Report
    
Weekly forecast for farming regions in Northern Europe.

Temperature: 15-22°C
Precipitation: Moderate rainfall expected
Wind conditions: Light to moderate

Crop recommendations:
- Delay wheat harvesting in western regions
- Optimal conditions for potato planting
- Monitor soil moisture levels

This report is issued by the European Agriculture Agency.
"""
    
    low_path = os.path.join(output_dir, "agriculture_report.txt")
    with open(low_path, "w", encoding="utf-8") as f:
        f.write(low_relevance_content)
    documents["low_relevance"] = low_path
    
    # Sample document with high urgency
    urgent_content = """URGENT: Cybersecurity Incident Response

IMMEDIATE ACTION REQUIRED

A critical vulnerability has been identified in e-commerce payment processing systems. All companies using affected systems must implement patches within 48 hours.

Affected Systems:
- Payment gateway version 2.1.x
- Customer data processing modules
- Mobile application backends

Steps Required:
1. Assess system exposure immediately
2. Apply security patches within 24 hours
3. Notify customers if data may be compromised
4. Report incident to regulatory authorities

Failure to comply may result in significant penalties and regulatory action.

Contact: security-emergency@regulatory-authority.eu
"""
    
    urgent_path = os.path.join(output_dir, "cybersecurity_urgent.txt")
    with open(urgent_path, "w", encoding="utf-8") as f:
        f.write(urgent_content)
    documents["urgent"] = urgent_path
    
    return documents


def create_corrupted_documents(output_dir: str) -> Dict[str, str]:
    """Create corrupted/invalid documents for error testing."""
    documents = {}
    
    # Empty file
    empty_path = os.path.join(output_dir, "empty.txt")
    with open(empty_path, "w") as f:
        pass  # Create empty file
    documents["empty"] = empty_path
    
    # Binary file with wrong extension
    binary_path = os.path.join(output_dir, "binary.txt")
    with open(binary_path, "wb") as f:
        f.write(b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09')
    documents["binary"] = binary_path
    
    # File with invalid encoding
    invalid_encoding_path = os.path.join(output_dir, "invalid_encoding.txt")
    with open(invalid_encoding_path, "wb") as f:
        f.write("Invalid encoding test".encode("utf-8") + b'\xff\xfe\xfd')
    documents["invalid_encoding"] = invalid_encoding_path
    
    return documents


def create_large_document(output_dir: str, size_mb: float = 1.0) -> str:
    """Create a large document for size limit testing."""
    large_path = os.path.join(output_dir, "large_document.txt")
    
    # Calculate how many repetitions we need
    base_text = "This is a large document for testing size limits. " * 100  # ~5KB
    repetitions = int((size_mb * 1024 * 1024) / len(base_text.encode('utf-8')))
    
    with open(large_path, "w", encoding="utf-8") as f:
        for _ in range(repetitions):
            f.write(base_text)
    
    return large_path


def get_sample_context() -> Dict[str, any]:
    """Get sample context configuration for testing."""
    return {
        "company_terms": ["testcorp", "test-company", "tc"],
        "core_industries": [
            "e-commerce",
            "online retail", 
            "digital marketplace",
            "technology"
        ],
        "primary_markets": [
            "european union",
            "eu",
            "germany", 
            "france",
            "poland"
        ],
        "secondary_markets": [
            "uk",
            "switzerland",
            "austria"
        ],
        "strategic_themes": [
            "digital transformation",
            "regulatory compliance",
            "data privacy",
            "cybersecurity",
            "competition law"
        ],
        "topic_patterns": {
            "data-protection": [
                "gdpr",
                "data privacy",
                "personal information",
                "data protection"
            ],
            "competition": [
                "antitrust",
                "competition law",
                "market dominance",
                "regulatory authority"
            ],
            "cybersecurity": [
                "cybersecurity",
                "data breach",
                "vulnerability",
                "security incident"
            ]
        },
        "direct_impact_keywords": [
            "must comply",
            "required",
            "mandatory",
            "penalty",
            "enforcement",
            "immediate action required"
        ]
    }