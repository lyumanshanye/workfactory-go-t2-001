"""Portable artifact DAG receipts; content correctness needs a domain verifier."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def signature(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def direct(root, name):
    if not isinstance(name, str) or not name or name in (".", "..") or "/" in name or "\\" in name:
        raise ValueError("direct artifact filename required")
    path = root / name
    if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("artifact symlink or path escape")
    return path


def config_read(path):
    config = json.loads(path.read_text())
    stages = config.get("stages", {})
    if not isinstance(stages, dict) or not stages or not config.get("source_hashes"):
        raise ValueError("explicit sources and DAG stages required")
    if not isinstance(config["source_hashes"], dict):
        raise ValueError("source hashes must be a mapping")
    for name, value in config["source_hashes"].items():
        direct(Path("."), name)
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError("invalid source SHA256")
    names = []
    for name, stage in stages.items():
        direct(Path("."), name)
        if not isinstance(stage, dict):
            raise ValueError("stage must be a mapping")
        deps, artifacts = stage.get("dependencies"), stage.get("artifacts")
        if (not isinstance(deps, list) or not isinstance(artifacts, list) or not artifacts
                or any(not isinstance(x, str) for x in deps + artifacts)
                or len(set(deps)) != len(deps) or len(set(artifacts)) != len(artifacts)
                or not set(deps) <= set(stages) or name in deps):
            raise ValueError("invalid stage dependencies/artifacts")
        for artifact in artifacts:
            direct(Path("."), artifact)
            if artifact == "workflow-state.json":
                raise ValueError("receipt cannot include itself")
        names.extend(artifacts)
    if len(set(names)) != len(names):
        raise ValueError("artifact has multiple producing stages")
    done, visiting = set(), set()
    def visit(name):
        if name in visiting:
            raise ValueError("workflow cycle")
        if name in done:
            return
        visiting.add(name)
        for dependency in stages[name]["dependencies"]:
            visit(dependency)
        visiting.remove(name)
        done.add(name)
    for name in stages:
        visit(name)
    return config


def source_manifest(config, inputs):
    current = {name:sha(direct(inputs, name)) for name in config["source_hashes"]}
    if current != config["source_hashes"]:
        raise ValueError("source snapshot changed")
    return current


def receipt_valid(name, receipts, config, config_sha, output, seen=None):
    seen = set() if seen is None else set(seen)
    if name in seen:
        return False
    seen.add(name)
    receipt = receipts.get(name, {})
    stage = config["stages"][name]
    if receipt.get("configuration") != config_sha or receipt.get("source_hashes") != config["source_hashes"]:
        return False
    try:
        artifacts = {file:sha(direct(output, file)) for file in stage["artifacts"]}
        dependencies = {dep:signature(receipts.get(dep, {})) for dep in stage["dependencies"]}
        return (receipt.get("artifacts") == artifacts and receipt.get("dependencies") == dependencies
                and all(receipt_valid(dep, receipts, config, config_sha, output, seen) for dep in stage["dependencies"]))
    except (OSError, ValueError):
        return False


def write_state(path, value):
    descriptor, temporary = tempfile.mkstemp(prefix=".workflow-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def seal(config_path, inputs, output, name):
    config = config_read(config_path)
    sources = source_manifest(config, inputs)
    if name not in config["stages"]:
        raise ValueError("unknown workflow stage")
    output.mkdir(parents=True, exist_ok=True)
    state_path = direct(output, "workflow-state.json")
    state = json.loads(state_path.read_text()) if state_path.exists() else dict(receipts={}, events=[])
    if not isinstance(state.get("receipts"), dict) or not isinstance(state.get("events"), list):
        raise ValueError("malformed workflow state")
    config_sha = sha(config_path)
    receipts = state["receipts"]
    stage = config["stages"][name]
    for dependency in stage["dependencies"]:
        if not receipt_valid(dependency, receipts, config, config_sha, output):
            raise ValueError("missing or stale dependency: " + dependency)
    artifacts = {}
    for file in stage["artifacts"]:
        path = direct(output, file)
        if not path.is_file() or path.stat().st_size == 0:
            raise ValueError("missing or empty stage artifact: " + file)
        artifacts[file] = sha(path)
    receipt = dict(configuration=config_sha, source_hashes=sources, artifacts=artifacts,
                   dependencies={dep:signature(receipts[dep]) for dep in stage["dependencies"]})
    receipts[name] = receipt
    state["events"].append(dict(sequence=len(state["events"]) + 1, stage=name, receipt_sha256=signature(receipt)))
    state["current"] = {stage:receipt_valid(stage, receipts, config, config_sha, output) for stage in config["stages"]}
    state["limitations"] = "Artifact/version dependency receipts only; not semantic correctness or unforgeable execution attestation. Native tool traces required for actual agent execution claims."
    write_state(state_path, state)
    return state


def inspect(config_path, inputs, output):
    config = config_read(config_path)
    source_manifest(config, inputs)
    state = json.loads(direct(output, "workflow-state.json").read_text())
    return {name:receipt_valid(name, state["receipts"], config, sha(config_path), output) for name in config["stages"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("seal", "inspect"))
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stage")
    args = parser.parse_args()
    result = seal(args.config, args.inputs, args.output, args.stage) if args.command == "seal" else inspect(args.config, args.inputs, args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2))
