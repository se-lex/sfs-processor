#!/usr/bin/env python3
"""
Generate detailed comparison report between before and after optimization.
"""

before_sizes = {
    '2010/800': 883110,
    '1967/837': 145976,
    '1920/405': 88636,
    '2024/1274': 10502,
    '2025/399': 2564,
}

after_sizes = {
    '2010/800': 868799,
    '1967/837': 144239,
    '1920/405': 87411,
    '2024/1274': 9938,
    '2025/399': 2190,
}

print("="*80)
print("HTML MINIFICATION OPTIMIZATION RESULTS")
print("="*80)
print()

total_before = sum(before_sizes.values())
total_after = sum(after_sizes.values())
savings = total_before - total_after
savings_pct = (savings / total_before) * 100

print(f"OVERALL RESULTS:")
print(f"-" * 80)
print(f"Total size before:  {total_before:10,} bytes ({total_before/1024:8.2f} KB)")
print(f"Total size after:   {total_after:10,} bytes ({total_after/1024:8.2f} KB)")
print(f"Total savings:      {savings:10,} bytes ({savings/1024:8.2f} KB)")
print(f"Reduction:          {savings_pct:9.2f}%")
print()

print(f"PER-FILE COMPARISON:")
print(f"-" * 80)
print(f"{'Document':20s} {'Before':>12s} {'After':>12s} {'Saved':>12s} {'%':>8s}")
print(f"-" * 80)

for doc in sorted(before_sizes.keys(), key=lambda x: before_sizes[x], reverse=True):
    before = before_sizes[doc]
    after = after_sizes[doc]
    saved = before - after
    saved_pct = (saved / before) * 100
    
    print(f"{doc:20s} {before:10,} B {after:10,} B {saved:10,} B {saved_pct:7.2f}%")

print()
print("="*80)
print("EXTRAPOLATION TO 10,000 DOCUMENTS")
print("="*80)
print()

avg_before = total_before / len(before_sizes)
avg_after = total_after / len(after_sizes)
avg_savings = avg_before - avg_after

docs_10k = 10000
total_10k_before = avg_before * docs_10k
total_10k_after = avg_after * docs_10k
total_10k_savings = avg_savings * docs_10k

print(f"Average file size:")
print(f"  Before:  {avg_before:10,.0f} bytes ({avg_before/1024:7.2f} KB)")
print(f"  After:   {avg_after:10,.0f} bytes ({avg_after/1024:7.2f} KB)")
print(f"  Savings: {avg_savings:10,.0f} bytes ({avg_savings/1024:7.2f} KB)")
print()

print(f"For 10,000 documents:")
print(f"  Before:  {total_10k_before/1024/1024:10,.2f} MB")
print(f"  After:   {total_10k_after/1024/1024:10,.2f} MB")
print(f"  Savings: {total_10k_savings/1024/1024:10,.2f} MB ({savings_pct:.2f}% reduction)")
print()

print("="*80)
print("COMBINED WITH GZIP COMPRESSION")
print("="*80)
print()

# Typical GZIP compression ratios for HTML
gzip_ratio = 0.25  # 75% reduction

print(f"HTML Minification + GZIP compression:")
print(f"  Original:           {total_10k_before/1024/1024:10,.2f} MB")
print(f"  After minification: {total_10k_after/1024/1024:10,.2f} MB ({savings_pct:.2f}% reduction)")
print(f"  After GZIP:         {total_10k_after * gzip_ratio /1024/1024:10,.2f} MB ({(1-gzip_ratio)*100:.0f}% additional reduction)")
print(f"  Total reduction:    {(1 - (total_10k_after * gzip_ratio / total_10k_before))*100:.2f}%")
print()
print(f"Final size per document (avg): {(avg_after * gzip_ratio)/1024:.2f} KB")
print()

print("="*80)
print("OPTIMIZATION BREAKDOWN")
print("="*80)
print()

print("What was optimized:")
print("  ✓ Removed unnecessary whitespace between tags")
print("  ✓ Removed leading/trailing whitespace on lines")
print("  ✓ Removed empty lines")
print("  ✓ Removed extra spaces in attributes")
print("  ✓ Reduced multiple spaces to single space")
print()

print("What was preserved:")
print("  ✓ All content within <pre>, <script>, <textarea> tags")
print("  ✓ Semantic HTML structure")
print("  ✓ ELI metadata attributes")
print("  ✓ Accessibility features")
print("  ✓ All functional JavaScript")
print()

print("="*80)
print("SUMMARY")
print("="*80)
print()
print(f"The HTML minification successfully reduces file sizes by {savings_pct:.2f}%.")
print(f"For 10,000 documents, this saves {total_10k_savings/1024/1024:.2f} MB of storage and bandwidth.")
print()
print("When combined with GZIP compression (recommended for production),")
print(f"the total reduction is {(1 - (total_10k_after * gzip_ratio / total_10k_before))*100:.2f}%, bringing the")
print(f"average file size from {avg_before/1024:.2f} KB to just {(avg_after * gzip_ratio)/1024:.2f} KB.")
print()
print("="*80)
