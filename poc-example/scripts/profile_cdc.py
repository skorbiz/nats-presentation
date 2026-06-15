#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_DURATION_SECONDS = 60
DEFAULT_INTERVAL_SECONDS = 5
DEFAULT_WAIT_FOR_STACK_SECONDS = 15
RUN_MODE = "raw_jetstream"

# Update these values here when you want a different load profile.
#
# Suggested comparison runs:
# 1. CDC baseline:
#    RUN_MODE = "cdc"
#    LOAD_INTERVAL_SECONDS = 5
#    LOAD_BATCH_SIZE = 1
#    LOAD_PAYLOAD_BYTES = 0
#
# 2. Raw JetStream baseline:
#    RUN_MODE = "raw_jetstream"
#    LOAD_INTERVAL_SECONDS = 5
#    LOAD_BATCH_SIZE = 1
#    LOAD_PAYLOAD_BYTES = 0
#
# 3. Larger messages:
#    LOAD_INTERVAL_SECONDS = 5
#    LOAD_BATCH_SIZE = 1
#    LOAD_PAYLOAD_BYTES = 8192
#
# 4. Heavier mixed load:
#    LOAD_INTERVAL_SECONDS = 0.01
#    LOAD_BATCH_SIZE = 10
#    LOAD_PAYLOAD_BYTES = 16384
#
# Practical workflow:
# - Compare CDC and raw_jetstream with the same load values below.
# - Edit ENABLED_SERVICES if you want to exclude specific services for one run.
LOAD_START_DELAY_SECONDS = 8
LOAD_INTERVAL_SECONDS = 0.00001
LOAD_BATCH_SIZE = 1
LOAD_PAYLOAD_BYTES = 16

DEFAULT_SERVICES_BY_MODE = {
    "cdc": [
        "nats",
        "postgres-cdc",
        "postgres-writer",
        "debezium-server",
        "jetstream-consumer-cdc",
    ],
    "raw_jetstream": [
        "nats",
        "jetstream-publisher-raw",
        "jetstream-consumer-raw",
    ],
}

ENABLED_SERVICES = DEFAULT_SERVICES_BY_MODE[RUN_MODE][:]


@dataclass
class ContainerSummary:
    samples: int = 0
    avg_cpu_percent: float = 0.0
    max_cpu_percent: float = 0.0
    max_mem_mib: float = 0.0
    net_rx_bytes_first: float | None = None
    net_rx_bytes_last: float | None = None
    net_tx_bytes_first: float | None = None
    net_tx_bytes_last: float | None = None


@dataclass
class ThroughputSummary:
    source_label: str
    start_count: int | None
    end_count: int | None
    completed_count: int | None
    theoretical_units_per_second: float | None
    theoretical_payload_bytes_per_second: float | None
    effective_active_seconds: float
    theoretical_units_during_active_window: float | None
    actual_units_per_second: float | None
    actual_payload_bytes_per_second: float | None


@dataclass
class ConsumerSummary:
    service_name: str
    received_messages: int | None
    acknowledged_messages: int | None
    last_stream_sequence: int | None


def run_command(
    args: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=check,
    )


def iso_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def timestamp_dirname() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def fetch_json(url: str) -> dict | None:
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return json.load(response)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None


def parse_percentage(value: str) -> float:
    return float(value.strip().rstrip("%"))


def parse_bytes(value: str) -> float:
    value = value.strip()
    if value == "0B":
        return 0.0

    suffixes = [
        ("TiB", 1024**4),
        ("GiB", 1024**3),
        ("MiB", 1024**2),
        ("KiB", 1024),
        ("TB", 1000**4),
        ("GB", 1000**3),
        ("MB", 1000**2),
        ("kB", 1000),
        ("B", 1),
    ]
    for suffix, multiplier in suffixes:
        if value.endswith(suffix):
            return float(value[: -len(suffix)].strip()) * multiplier
    raise ValueError(f"Unsupported byte value: {value}")


def parse_mem_usage(value: str) -> tuple[float, float]:
    used, _, total = value.partition("/")
    return parse_bytes(used), parse_bytes(total)


def parse_io_pair(value: str) -> tuple[float, float]:
    left, _, right = value.partition("/")
    return parse_bytes(left), parse_bytes(right)


def mib(value_in_bytes: float) -> float:
    return value_in_bytes / (1024**2)


def format_mib(value_in_bytes: float) -> str:
    return f"{mib(value_in_bytes):.1f} MiB"


def format_bytes_compact(value_in_bytes: float) -> str:
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    value = float(value_in_bytes)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TiB"


def collect_container_ids(compose_env: dict[str, str], cwd: Path) -> list[str]:
    container_ids: list[str] = []
    for service in ENABLED_SERVICES:
        result = run_command(
            ["docker", "compose", "--profile", "cdc", "ps", "-q", service],
            cwd=cwd,
            env=compose_env,
            check=False,
        )
        container_id = result.stdout.strip()
        if container_id:
            container_ids.append(container_id)
    return container_ids


def collect_docker_stats(container_ids: list[str], cwd: Path) -> list[dict[str, str]]:
    result = run_command(
        [
            "docker",
            "stats",
            "--no-stream",
            "--format",
            "{{json .}}",
            *container_ids,
        ],
        cwd=cwd,
    )
    rows: list[dict[str, str]] = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def query_inventory_row_count(compose_env: dict[str, str], cwd: Path) -> int | None:
    result = run_command(
        [
            "docker",
            "compose",
            "--profile",
            "cdc",
            "exec",
            "-T",
            "postgres-cdc",
            "psql",
            "-U",
            "postgres",
            "-d",
            "inventory",
            "-tA",
            "-c",
            "SELECT COUNT(*) FROM public.inventory_items;",
        ],
        cwd=cwd,
        env=compose_env,
        check=False,
    )
    output = result.stdout.strip()
    if result.returncode != 0 or not output:
        return None
    try:
        return int(output)
    except ValueError:
        return None


def query_raw_publisher_count(compose_env: dict[str, str], cwd: Path) -> int | None:
    result = run_command(
        [
            "docker",
            "compose",
            "--profile",
            "cdc",
            "exec",
            "-T",
            "jetstream-publisher-raw",
            "python",
            "-c",
            ("import json; print(json.load(open('/tmp/raw_publisher_stats.json'))['published_messages'])"),
        ],
        cwd=cwd,
        env=compose_env,
        check=False,
    )
    output = result.stdout.strip()
    if result.returncode != 0 or not output:
        return None
    try:
        return int(output)
    except ValueError:
        return None


def query_consumer_stats(service_name: str, compose_env: dict[str, str], cwd: Path) -> ConsumerSummary | None:
    result = run_command(
        [
            "docker",
            "compose",
            "--profile",
            "cdc",
            "exec",
            "-T",
            service_name,
            "python",
            "-c",
            ("import json; print(json.dumps(json.load(open('/tmp/jetstream_consumer_stats.json'))))"),
        ],
        cwd=cwd,
        env=compose_env,
        check=False,
    )
    output = result.stdout.strip()
    if result.returncode != 0 or not output:
        return None
    try:
        payload = json.loads(output)
    except json.JSONDecodeError:
        return None
    return ConsumerSummary(
        service_name=service_name,
        received_messages=payload.get("received_messages"),
        acknowledged_messages=payload.get("acknowledged_messages"),
        last_stream_sequence=payload.get("last_stream_sequence"),
    )


def summarize_stats(csv_path: Path) -> dict[str, ContainerSummary]:
    per_container: dict[str, ContainerSummary] = defaultdict(ContainerSummary)
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            summary = per_container[row["name"]]
            summary.samples += 1

            cpu_percent = parse_percentage(row["cpu_perc"])
            summary.avg_cpu_percent += cpu_percent
            summary.max_cpu_percent = max(summary.max_cpu_percent, cpu_percent)

            mem_used_bytes, _ = parse_mem_usage(row["mem_usage"])
            summary.max_mem_mib = max(summary.max_mem_mib, mib(mem_used_bytes))

            net_rx_bytes, net_tx_bytes = parse_io_pair(row["net_io"])
            if summary.net_rx_bytes_first is None:
                summary.net_rx_bytes_first = net_rx_bytes
                summary.net_tx_bytes_first = net_tx_bytes
            summary.net_rx_bytes_last = net_rx_bytes
            summary.net_tx_bytes_last = net_tx_bytes

    for summary in per_container.values():
        if summary.samples:
            summary.avg_cpu_percent /= summary.samples

    return dict(sorted(per_container.items()))


def read_ndjson(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def build_throughput_summary(
    *,
    source_label: str,
    start_count: int | None,
    end_count: int | None,
    duration_seconds: int,
) -> ThroughputSummary:
    completed_count = None
    if start_count is not None and end_count is not None:
        completed_count = max(0, end_count - start_count)

    effective_active_seconds = max(0.0, duration_seconds - LOAD_START_DELAY_SECONDS)

    theoretical_units_per_second = None
    theoretical_payload_bytes_per_second = None
    theoretical_units_during_active_window = None
    if LOAD_INTERVAL_SECONDS > 0:
        theoretical_units_per_second = LOAD_BATCH_SIZE / LOAD_INTERVAL_SECONDS
        theoretical_payload_bytes_per_second = theoretical_units_per_second * LOAD_PAYLOAD_BYTES
        theoretical_units_during_active_window = theoretical_units_per_second * effective_active_seconds

    actual_units_per_second = None
    actual_payload_bytes_per_second = None
    if completed_count is not None and duration_seconds > 0:
        actual_units_per_second = completed_count / duration_seconds
        actual_payload_bytes_per_second = actual_units_per_second * LOAD_PAYLOAD_BYTES

    return ThroughputSummary(
        source_label=source_label,
        start_count=start_count,
        end_count=end_count,
        completed_count=completed_count,
        theoretical_units_per_second=theoretical_units_per_second,
        theoretical_payload_bytes_per_second=theoretical_payload_bytes_per_second,
        effective_active_seconds=effective_active_seconds,
        theoretical_units_during_active_window=theoretical_units_during_active_window,
        actual_units_per_second=actual_units_per_second,
        actual_payload_bytes_per_second=actual_payload_bytes_per_second,
    )


def nats_key_figures(varz_rows: list[dict], connz_rows: list[dict], jsz_rows: list[dict]) -> list[str]:
    if not varz_rows:
        return ["NATS key figures: no monitoring snapshots captured"]

    first_varz = varz_rows[0]["payload"]
    last_varz = varz_rows[-1]["payload"]
    lines = [
        "NATS key figures:",
        (f"  connections {first_varz.get('connections', 0)} -> {last_varz.get('connections', 0)}"),
        (
            f"  in msgs {first_varz.get('in_msgs', 0)} -> "
            f"{last_varz.get('in_msgs', 0)}, out msgs {first_varz.get('out_msgs', 0)} -> "
            f"{last_varz.get('out_msgs', 0)}"
        ),
        (
            f"  in bytes {format_bytes_compact(first_varz.get('in_bytes', 0))} -> "
            f"{format_bytes_compact(last_varz.get('in_bytes', 0))}, out bytes "
            f"{format_bytes_compact(first_varz.get('out_bytes', 0))} -> "
            f"{format_bytes_compact(last_varz.get('out_bytes', 0))}"
        ),
    ]

    if connz_rows:
        lines.append(f"  tracked client connections in connz: {connz_rows[-1]['payload'].get('num_connections', 0)}")

    if jsz_rows:
        payload = jsz_rows[-1]["payload"]
        lines.append(
            f"  jetstream memory {format_bytes_compact(payload.get('memory', 0))}, "
            f"storage {format_bytes_compact(payload.get('storage', 0))}, "
            f"streams {payload.get('streams', 0)}, consumers {payload.get('consumers', 0)}"
        )

    return lines


def write_summary(
    summary_path: Path,
    output_dir: Path,
    stats_path: Path,
    varz_path: Path,
    connz_path: Path,
    jsz_path: Path,
    per_container: dict[str, ContainerSummary],
    throughput: ThroughputSummary,
    consumer_summaries: list[ConsumerSummary],
    duration_seconds: int,
    interval_seconds: int,
) -> str:
    lines = [
        f"Profile output: {output_dir}",
        f"docker stats samples: {stats_path}",
        f"nats varz samples: {varz_path}",
        f"nats connz samples: {connz_path}",
        f"nats jsz samples: {jsz_path}",
        "",
        "Run configuration:",
        f"  run_mode={RUN_MODE}",
        f"  enabled_services={', '.join(ENABLED_SERVICES)}",
        f"  duration_seconds={duration_seconds}",
        f"  interval_seconds={interval_seconds}",
        f"  load_start_delay_seconds={LOAD_START_DELAY_SECONDS}",
        f"  load_interval_seconds={LOAD_INTERVAL_SECONDS}",
        f"  load_batch_size={LOAD_BATCH_SIZE}",
        f"  load_payload_bytes={LOAD_PAYLOAD_BYTES}",
        "",
        "Load throughput:",
    ]

    if throughput.completed_count is None:
        lines.append(f"  actual {throughput.source_label} count: unavailable")
    else:
        actual_payload_bytes_per_second = throughput.actual_payload_bytes_per_second
        assert actual_payload_bytes_per_second is not None
        lines.extend(
            [
                f"  {throughput.source_label}_count_start: {throughput.start_count}",
                f"  {throughput.source_label}_count_end: {throughput.end_count}",
                f"  completed_{throughput.source_label}_during_run: {throughput.completed_count}",
                f"  actual_{throughput.source_label}_per_second: {throughput.actual_units_per_second:.2f}",
                (f"  actual_raw_payload_per_second: {format_bytes_compact(actual_payload_bytes_per_second)}"),
            ]
        )

    if throughput.theoretical_units_per_second is None:
        lines.append("  theoretical rate: unavailable because load interval is <= 0")
    else:
        theoretical_payload_bytes_per_second = throughput.theoretical_payload_bytes_per_second
        assert theoretical_payload_bytes_per_second is not None
        lines.extend(
            [
                f"  effective_active_seconds: {throughput.effective_active_seconds:.2f}",
                f"  theoretical_{throughput.source_label}_per_second: {throughput.theoretical_units_per_second:.2f}",
                (f"  theoretical_raw_payload_per_second: {format_bytes_compact(theoretical_payload_bytes_per_second)}"),
                (
                    f"  theoretical_{throughput.source_label}_during_active_window: "
                    f"{throughput.theoretical_units_during_active_window:.0f}"
                ),
            ]
        )

    lines.extend(["", "Consumer validation:"])
    if not consumer_summaries:
        lines.append("  consumer stats: unavailable")
    else:
        for consumer_summary in consumer_summaries:
            lines.extend(
                [
                    f"  {consumer_summary.service_name}",
                    f"    received_messages: {consumer_summary.received_messages}",
                    f"    acknowledged_messages: {consumer_summary.acknowledged_messages}",
                    f"    last_stream_sequence: {consumer_summary.last_stream_sequence}",
                ]
            )
            if throughput.completed_count is not None and consumer_summary.received_messages is not None:
                delivery_ratio = (
                    consumer_summary.received_messages / throughput.completed_count
                    if throughput.completed_count
                    else 0.0
                )
                lines.append(f"    received_vs_produced_ratio: {delivery_ratio:.3f}")
            lines.append("")

    lines.extend(
        [
            "",
            "Container key figures:",
        ]
    )

    for container_name, summary in per_container.items():
        rx_delta = (summary.net_rx_bytes_last or 0) - (summary.net_rx_bytes_first or 0)
        tx_delta = (summary.net_tx_bytes_last or 0) - (summary.net_tx_bytes_first or 0)
        lines.extend(
            [
                f"  {container_name}",
                f"    samples: {summary.samples}",
                f"    avg_cpu: {summary.avg_cpu_percent:.2f}%",
                f"    max_cpu: {summary.max_cpu_percent:.2f}%",
                f"    max_mem: {summary.max_mem_mib:.1f} MiB",
                f"    net_rx_delta: {format_bytes_compact(rx_delta)}",
                f"    net_tx_delta: {format_bytes_compact(tx_delta)}",
                "",
            ]
        )

    lines.extend(
        nats_key_figures(
            read_ndjson(varz_path),
            read_ndjson(connz_path),
            read_ndjson(jsz_path),
        )
    )

    summary_text = "\n".join(lines) + "\n"
    summary_path.write_text(summary_text, encoding="utf-8")
    return summary_text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Profile the NATS + Debezium CDC stack.")
    parser.add_argument(
        "duration_seconds",
        nargs="?",
        type=int,
        default=DEFAULT_DURATION_SECONDS,
        help=f"How long to sample for. Default: {DEFAULT_DURATION_SECONDS}",
    )
    parser.add_argument(
        "interval_seconds",
        nargs="?",
        type=int,
        default=DEFAULT_INTERVAL_SECONDS,
        help=f"How often to sample. Default: {DEFAULT_INTERVAL_SECONDS}",
    )
    parser.add_argument(
        "output_dir",
        nargs="?",
        default=f"profiles/{timestamp_dirname()}",
        help="Where to store the profile output.",
    )
    return parser.parse_args()


def main() -> int:
    if not shutil_which("docker"):
        print("docker is required", file=sys.stderr)
        return 1

    args = parse_args()
    cwd = Path(__file__).resolve().parent.parent
    output_dir = (cwd / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    compose_env = os.environ.copy()
    compose_env.update(
        {
            "WRITER_START_DELAY_SECONDS": str(LOAD_START_DELAY_SECONDS),
            "WRITER_INSERT_INTERVAL_SECONDS": str(LOAD_INTERVAL_SECONDS),
            "WRITER_BATCH_SIZE": str(LOAD_BATCH_SIZE),
            "WRITER_PAYLOAD_BYTES": str(LOAD_PAYLOAD_BYTES),
            "RAW_PUBLISHER_START_DELAY_SECONDS": str(LOAD_START_DELAY_SECONDS),
            "RAW_PUBLISHER_INTERVAL_SECONDS": str(LOAD_INTERVAL_SECONDS),
            "RAW_PUBLISHER_BATCH_SIZE": str(LOAD_BATCH_SIZE),
            "RAW_PUBLISHER_PAYLOAD_BYTES": str(LOAD_PAYLOAD_BYTES),
        }
    )
    stats_path = output_dir / "docker-stats.csv"
    varz_path = output_dir / "nats-varz.ndjson"
    connz_path = output_dir / "nats-connz.ndjson"
    jsz_path = output_dir / "nats-jsz.ndjson"
    summary_path = output_dir / "summary.txt"
    try:
        print("Resetting CDC stack and volumes before profiling...")
        run_command(
            ["docker", "compose", "--profile", "cdc", "down", "-v"],
            cwd=cwd,
            env=compose_env,
            check=False,
        )

        print("Starting CDC stack...")
        run_command(
            ["docker", "compose", "--profile", "cdc", "up", "-d", "--build", *ENABLED_SERVICES],
            cwd=cwd,
            env=compose_env,
        )

        print("Waiting for key services to be running...")
        time.sleep(DEFAULT_WAIT_FOR_STACK_SECONDS)

        start_count = None
        throughput_source_label = "messages"
        if RUN_MODE == "cdc" and "postgres-cdc" in ENABLED_SERVICES:
            start_count = query_inventory_row_count(compose_env, cwd)
            throughput_source_label = "rows"
        elif RUN_MODE == "raw_jetstream" and "jetstream-publisher-raw" in ENABLED_SERVICES:
            start_count = query_raw_publisher_count(compose_env, cwd)
            throughput_source_label = "messages"

        container_ids = collect_container_ids(compose_env, cwd)
        if not container_ids:
            print("No running CDC containers found", file=sys.stderr)
            return 1

        with stats_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "timestamp",
                    "container",
                    "name",
                    "cpu_perc",
                    "mem_usage",
                    "mem_perc",
                    "net_io",
                    "block_io",
                    "pids",
                ],
            )
            writer.writeheader()

            end_time = time.time() + args.duration_seconds
            print(f"Capturing stats for {args.duration_seconds}s at {args.interval_seconds}s intervals...")
            while time.time() < end_time:
                timestamp = iso_now()
                stats_rows = collect_docker_stats(container_ids, cwd)
                for row in stats_rows:
                    writer.writerow(
                        {
                            "timestamp": timestamp,
                            "container": row["Container"],
                            "name": row["Name"],
                            "cpu_perc": row["CPUPerc"],
                            "mem_usage": row["MemUsage"],
                            "mem_perc": row["MemPerc"],
                            "net_io": row["NetIO"],
                            "block_io": row["BlockIO"],
                            "pids": row["PIDs"],
                        }
                    )
                handle.flush()

                for _name, url, path in [  # noqa: B007
                    ("varz", "http://localhost:8222/varz", varz_path),
                    ("connz", "http://localhost:8222/connz?subs=1", connz_path),
                    (
                        "jsz",
                        "http://localhost:8222/jsz?accounts=true&streams=true&consumers=true",
                        jsz_path,
                    ),
                ]:
                    payload = fetch_json(url)
                    if payload is None:
                        continue
                    with path.open("a", encoding="utf-8") as json_handle:
                        json_handle.write(json.dumps({"timestamp": timestamp, "payload": payload}) + "\n")

                time.sleep(args.interval_seconds)

        end_count = None
        if RUN_MODE == "cdc" and "postgres-cdc" in ENABLED_SERVICES:
            end_count = query_inventory_row_count(compose_env, cwd)
        elif RUN_MODE == "raw_jetstream" and "jetstream-publisher-raw" in ENABLED_SERVICES:
            end_count = query_raw_publisher_count(compose_env, cwd)
        per_container = summarize_stats(stats_path)
        consumer_summaries: list[ConsumerSummary] = []
        for candidate_service in ["jetstream-consumer-cdc", "jetstream-consumer-raw"]:
            if candidate_service in ENABLED_SERVICES:
                summary = query_consumer_stats(candidate_service, compose_env, cwd)
                if summary is not None:
                    consumer_summaries.append(summary)
        throughput = build_throughput_summary(
            source_label=throughput_source_label,
            start_count=start_count,
            end_count=end_count,
            duration_seconds=args.duration_seconds,
        )
        summary_text = write_summary(
            summary_path,
            output_dir,
            stats_path,
            varz_path,
            connz_path,
            jsz_path,
            per_container,
            throughput,
            consumer_summaries,
            args.duration_seconds,
            args.interval_seconds,
        )

        print("Profile capture finished.")
        print(summary_text, end="")
        return 0
    finally:
        print("Cleaning up CDC stack and volumes after profiling...")
        run_command(
            ["docker", "compose", "--profile", "cdc", "down", "-v"],
            cwd=cwd,
            env=compose_env,
            check=False,
        )


def shutil_which(binary: str) -> str | None:
    for path in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(path) / binary
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


if __name__ == "__main__":
    raise SystemExit(main())
