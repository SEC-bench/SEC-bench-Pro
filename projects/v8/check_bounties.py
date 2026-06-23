#!/usr/bin/env python3
"""
Script to check VRP bounties in v8 benchmark instances.
Parses Report.md files and extracts VRP-Reward values.
"""

import re
from pathlib import Path

VRP_STATUS_NOTES = {
    'DUP': 'duplicate report',
    'INT': 'reported by internal staff like Google',
    'CRN': 'churn, found within 3 days of the commit',
    'TBD': 'reward still to be determined',
    'BUG': 'not applicable to VRP',
}


def read_vrp_reward(report_path):
    """Extract the raw and numeric VRP-Reward values from a Report.md file."""
    try:
        with open(report_path, 'r') as f:
            for line in f:
                match = re.match(r'^VRP-Reward:\s*(.+)$', line.strip())
                if match:
                    raw_value = match.group(1).strip()
                    # Try to parse as integer
                    try:
                        return raw_value, int(raw_value)
                    except ValueError:
                        # Non-numeric value (e.g., "DUP", "(unknown)", etc.)
                        return raw_value, None
    except Exception as e:
        print(f"Error reading {report_path}: {e}")
        return None, None
    return None, None


def format_vrp_status(raw_value):
    """Render a human-readable status for non-bounty VRP labels."""
    if raw_value is None:
        return "N/A"

    note = VRP_STATUS_NOTES.get(raw_value.upper())
    if note:
        return f"{raw_value} ({note})"
    return raw_value

def main():
    v8_dir = Path(__file__).resolve().parent
    
    bounty_instances = []
    no_bounty_instances = []
    total_bounty = 0
    
    # Find all instance directories (numeric names)
    for instance_dir in sorted(v8_dir.iterdir()):
        if not instance_dir.is_dir():
            continue
        if not instance_dir.name.isdigit():
            continue
            
        report_path = instance_dir / 'Report.md'
        if not report_path.exists():
            no_bounty_instances.append((instance_dir.name, 'No Report.md'))
            continue
        
        raw_value, reward = read_vrp_reward(report_path)
        
        if reward is not None and reward > 0:
            bounty_instances.append((instance_dir.name, reward))
            total_bounty += reward
        else:
            no_bounty_instances.append((instance_dir.name, format_vrp_status(raw_value)))
    
    # Sort by bounty amount (descending) for bounty instances
    bounty_instances.sort(key=lambda x: x[1], reverse=True)
    
    # Print results
    print("=" * 60)
    print("VRP BOUNTY ANALYSIS FOR V8 INSTANCES")
    print("=" * 60)
    
    print(f"\n📊 SUMMARY")
    print(f"   Total instances:          {len(bounty_instances) + len(no_bounty_instances)}")
    print(f"   Instances with bounty:    {len(bounty_instances)}")
    print(f"   Instances without bounty: {len(no_bounty_instances)}")
    print(f"   💰 TOTAL BOUNTY:          ${total_bounty:,}")
    
    if bounty_instances:
        print(f"\n🏆 INSTANCES WITH BOUNTIES (sorted by amount):")
        print(f"   {'Instance ID':<15} {'Bounty':>7}")
        print(f"   {'-'*15} {'-'*10}")
        for instance_id, reward in bounty_instances:
            print(f"   {instance_id:<15} ${reward:>7,}")
    
    if no_bounty_instances:
        print(f"\n📋 INSTANCES WITHOUT BOUNTIES:")
        print(f"   {'Instance ID':<15} Status")
        print(f"   {'-'*15} {'-'*45}")
        for instance_id, status in no_bounty_instances[:20]:  # Show first 20
            print(f"   {instance_id:<15} {status}")
        if len(no_bounty_instances) > 20:
            print(f"   ... and {len(no_bounty_instances) - 20} more")
    
    print("\n" + "=" * 60)

if __name__ == '__main__':
    main()
