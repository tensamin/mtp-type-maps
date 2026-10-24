#!/usr/bin/env python3
"""Synchronize the development protocol's single 1.0 map across repositories."""

import argparse
from pathlib import Path
import re


OPERATIONS = {
    name: 226 + index
    for index, name in enumerate([
        "CallCommand", "CallCommandResult", "CallSnapshotGet", "CallSnapshot",
        "CallStateChanged", "CallJoinAuthorize", "CallJoinGrant",
        "CallKeyEnvelopeStage", "CallKeyEnvelopeGet", "CallKeyEnvelopeRevoke",
        "CallKeyEnvelopeActivate", "CallKeyEpochChanged",
    ])
}
FIELDS = {"CallPayload": 256}


def read_map(text, version):
    """Read this repository's flat numeric type-map schema without dependencies."""
    result = {"CommunicationTypes": {}, "DataTypes": {}}
    active = False
    category = None
    for line in text.splitlines():
        if match := re.fullmatch(r'  "([0-9]+\.[0-9]+)":', line):
            active = match[1] == version
            category = None
        elif active and (match := re.fullmatch(r"    (CommunicationTypes|DataTypes):", line)):
            category = match[1]
        elif active and category and line.strip() and not line.lstrip().startswith("#"):
            match = re.fullmatch(r"      ([A-Za-z][A-Za-z0-9]*): ([0-9]+)", line)
            if not match:
                raise ValueError(f"Unsupported type-map line: {line!r}")
            name, number = match[1], int(match[2])
            if name in result[category] or number in result[category].values():
                raise ValueError(f"Duplicate name or ID in {category}: {line.strip()}")
            if not 32 <= number <= 65535:
                raise ValueError(f"Reserved or out-of-range ID: {line.strip()}")
            result[category][name] = number
    if not all(result.values()):
        raise ValueError(f"Missing type-map version {version}")
    return result


def merge(target, extra):
    for name, number in extra.items():
        if name in target and target[name] != number:
            raise ValueError(f"Conflicting ID for {name}")
        if any(key != name and value == number for key, value in target.items()):
            raise ValueError(f"ID {number} already assigned to another type")
        target[name] = number


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check without writing")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    paths = [root / "type-maps.yaml", root.parent / "tau/type-maps.yaml"]
    paths += [root.parent / repo / "mtp-type-maps/type-maps.yaml" for repo in ("omikron", "iota", "omega", "client")]
    maps = {path: read_map(path.read_text(), "1.0") for path in paths}
    current = {category: {} for category in ("CommunicationTypes", "DataTypes")}
    for mapping in maps.values():
        for category, entries in mapping.items():
            merge(current[category], entries)
    merge(current["CommunicationTypes"], OPERATIONS)
    merge(current["DataTypes"], FIELDS)
    generated = 'protocol_version: "1.0"\n\ntype_maps:\n  "1.0":\n'
    for category, entries in current.items():
        generated += f"    {category}:\n"
        generated += "".join(f"      {name}: {number}\n" for name, number in sorted(entries.items(), key=lambda item: item[1]))
        generated += "\n"
    stale = []
    for path in paths:
        text = path.read_text()
        output = generated.rstrip() + "\n"
        if text != output:
            stale.append(str(path))
            if not args.check:
                path.write_text(output)
    if args.check and stale:
        parser.exit(1, "Stale call maps:\n" + "\n".join(stale) + "\n")
    print(f"{'Checked' if args.check else 'Synchronized'} {len(paths)} identical 1.0 maps")


if __name__ == "__main__":
    main()
