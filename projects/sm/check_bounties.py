#!/usr/bin/env python3
"""SpiderMonkey VRP bounty aggregator.

Reads ``meta.json["vrp"]`` (canonical for the SpiderMonkey dataset; usually
``null`` because Mozilla does not run a structured per-bug VRP comparable to
Chrome's). Falls back to a ``VRP-Reward:`` line in Report.md for parity with
v8/check_bounties.py if a future entry uses that style.
"""

import json
import re
from pathlib import Path

VRP_STATUS_NOTES = {
    "DUP": "duplicate report",
    "INT": "reported by internal staff",
    "CRN": "churn, found within 3 days of the commit",
    "TBD": "reward still to be determined",
    "BUG": "not applicable to VRP",
}


def read_vrp_from_report(report_path: Path) -> tuple[str | None, int | None]:
    """Extract a ``VRP-Reward:`` line from Report.md if present."""
    try:
        for line in report_path.read_text(encoding="utf-8", errors="replace").splitlines():
            match = re.match(r"^VRP-Reward:\s*(.+)$", line.strip())
            if match:
                raw_value = match.group(1).strip()
                try:
                    return raw_value, int(raw_value)
                except ValueError:
                    return raw_value, None
    except FileNotFoundError:
        return None, None
    except OSError as exc:
        print(f"Error reading {report_path}: {exc}")
        return None, None
    return None, None


def read_vrp_from_meta(meta_path: Path) -> tuple[str | None, int | None]:
    """Pull ``vrp`` field from meta.json. Accepts int, numeric string, or null."""
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"Error reading {meta_path}: {exc}")
        return None, None

    raw = meta.get("vrp")
    if raw is None:
        return None, None
    if isinstance(raw, (int, float)) and raw > 0:
        return str(int(raw)), int(raw)
    if isinstance(raw, str):
        try:
            return raw, int(raw)
        except ValueError:
            return raw, None
    return str(raw), None


def format_vrp_status(raw_value: str | None) -> str:
    if raw_value is None:
        return "null (no VRP recorded)"
    note = VRP_STATUS_NOTES.get(raw_value.upper())
    if note:
        return f"{raw_value} ({note})"
    return raw_value


def main() -> None:
    sm_dir = Path(__file__).resolve().parent

    bounty_instances: list[tuple[str, int]] = []
    no_bounty_instances: list[tuple[str, str]] = []
    total_bounty = 0

    for instance_dir in sorted(sm_dir.iterdir()):
        if not instance_dir.is_dir() or not instance_dir.name.isdigit():
            continue

        meta_path = instance_dir / "meta.json"
        report_path = instance_dir / "Report.md"

        # Prefer meta.json["vrp"] (canonical); fall back to Report.md.
        raw_value: str | None
        reward: int | None
        raw_value, reward = (None, None)

        if meta_path.exists():
            raw_value, reward = read_vrp_from_meta(meta_path)

        if reward is None and report_path.exists():
            r2, n2 = read_vrp_from_report(report_path)
            if n2 is not None or r2 is not None:
                raw_value, reward = r2, n2

        if reward is not None and reward > 0:
            bounty_instances.append((instance_dir.name, reward))
            total_bounty += reward
        else:
            no_bounty_instances.append((instance_dir.name, format_vrp_status(raw_value)))

    bounty_instances.sort(key=lambda x: x[1], reverse=True)

    print("=" * 60)
    print("VRP BOUNTY ANALYSIS FOR SPIDERMONKEY INSTANCES")
    print("=" * 60)

    total = len(bounty_instances) + len(no_bounty_instances)
    print(f"\nSUMMARY")
    print(f"   Total instances:          {total}")
    print(f"   Instances with bounty:    {len(bounty_instances)}")
    print(f"   Instances without bounty: {len(no_bounty_instances)}")
    print(f"   TOTAL BOUNTY:             ${total_bounty:,}")

    if bounty_instances:
        print(f"\nINSTANCES WITH BOUNTIES (sorted by amount):")
        print(f"   {'Instance ID':<15} {'Bounty':>10}")
        print(f"   {'-'*15} {'-'*10}")
        for instance_id, reward in bounty_instances:
            print(f"   {instance_id:<15} ${reward:>9,}")

    if no_bounty_instances:
        print(f"\nINSTANCES WITHOUT BOUNTIES:")
        print(f"   {'Instance ID':<15} Status")
        print(f"   {'-'*15} {'-'*45}")
        for instance_id, status in no_bounty_instances[:20]:
            print(f"   {instance_id:<15} {status}")
        if len(no_bounty_instances) > 20:
            print(f"   ... and {len(no_bounty_instances) - 20} more")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
