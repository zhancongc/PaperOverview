#!/usr/bin/env python3
"""
调试特定论文的数据
"""
import json

json_file = "test_cas_review_20260405_142702.json"

with open(json_file, "r", encoding="utf-8") as f:
    result = json.load(f)

cited_papers = result["cited_papers"]

print("查找有问题的论文...\n")

for i, paper in enumerate(cited_papers, 1):
    title = paper.get("title", "")
    if "Explainable AI Insights" in title or "Numerical and Symbolic Computation" in title:
        print(f"[{i}] {title}")
        print(f"    Authors: {paper.get('authors', [])}")
        print(f"    DOI: {paper.get('doi', '')}")
        print(f"    Venue: {paper.get('venue_name', '')}")
        print(f"    All fields: {list(paper.keys())}")
        print(f"    Full data: {json.dumps(paper, ensure_ascii=False, indent=4)[:500]}")
        print()
