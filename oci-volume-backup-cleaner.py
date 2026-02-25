#!/usr/bin/env python3

"""
OCI Backup Cleanup Script

Scans Boot Volume and Block Volume backups in a compartment
and removes older backups while keeping the newest N per volume.

Supports:
- dry run preview
- throttling delay between deletes
- optional boot/block filtering
- parallel deletion workers
- custom config/profile
"""

import argparse
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import oci
from oci.config import from_file, validate_config
from oci.core import BlockstorageClient
from oci.exceptions import ServiceError, ConfigFileNotFound


DEFAULT_CONFIG = "~/.oci/config"
DEFAULT_PROFILE = "DEFAULT"


# ----------------------------------------------------------
# logging setup
# ----------------------------------------------------------
def setup_logging(level: str, logfile: str = None):

    logger = logging.getLogger("oci_backup_cleanup")
    logger.setLevel(getattr(logging, level.upper()))
    logger.handlers.clear()

    fmt = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s",
        "%Y-%m-%d %H:%M:%S"
    )

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    if logfile:
        fh = logging.FileHandler(logfile)
        fh.setFormatter(fmt)
        logger.addHandler(fh)

    return logger


# ----------------------------------------------------------
# client init
# ----------------------------------------------------------
def init_client(config_path, profile):

    config = from_file(config_path, profile)
    validate_config(config)

    retry = oci.retry.RetryStrategyBuilder(
        max_attempts=6,
        service_error_retry_on_any_5xx=True,
        service_error_retry_config={429: []},
        total_elapsed_time_seconds=300
    ).get_retry_strategy()

    return BlockstorageClient(config, retry_strategy=retry)


# ----------------------------------------------------------
# list backups
# ----------------------------------------------------------
def list_backups(client, compartment_id, boot=True):

    if boot:
        result = oci.pagination.list_call_get_all_results(
            client.list_boot_volume_backups,
            compartment_id=compartment_id
        ).data
    else:
        result = oci.pagination.list_call_get_all_results(
            client.list_volume_backups,
            compartment_id=compartment_id
        ).data

    # only AVAILABLE backups are safe to delete
    return [b for b in result if b.lifecycle_state == "AVAILABLE"]


# ----------------------------------------------------------
# group backups by volume
# ----------------------------------------------------------
def group_by_volume(backups, boot=True):

    grouped = {}

    for b in backups:
        vol = b.boot_volume_id if boot else b.volume_id
        grouped.setdefault(vol, []).append(b)

    return grouped


# ----------------------------------------------------------
# delete one backup
# ----------------------------------------------------------
def delete_one(client, backup_id, boot, sleep):

    try:
        if boot:
            client.delete_boot_volume_backup(backup_id)
        else:
            client.delete_volume_backup(backup_id)

        if sleep:
            time.sleep(sleep)

        return True, backup_id, None

    except ServiceError as e:
        return False, backup_id, f"{e.status} {e.message}"

    except Exception as e:
        return False, backup_id, str(e)


# ----------------------------------------------------------
# cleanup logic
# ----------------------------------------------------------
def cleanup(client, grouped, keep, dry_run, workers, boot, sleep, logger):

    to_delete = []

    for vol_id, backups in grouped.items():

        backups_sorted = sorted(backups, key=lambda x: x.time_created)

        # always keep at least one newest backup
        keep_safe = max(keep, 1)

        delete_candidates = backups_sorted[:-keep_safe]

        for b in delete_candidates:
            to_delete.append(b)

    if not to_delete:
        logger.info("Nothing to delete.")
        return 0, 0

    logger.info(f"{len(to_delete)} backups marked for deletion")

    if dry_run:
        for b in to_delete:
            logger.info(f"[DRY RUN] {b.display_name}  ({b.id})")
        return len(to_delete), 0

    deleted = 0
    errors = 0

    with ThreadPoolExecutor(max_workers=workers) as pool:

        futures = [
            pool.submit(delete_one, client, b.id, boot, sleep)
            for b in to_delete
        ]

        for f in as_completed(futures):
            ok, bid, err = f.result()

            if ok:
                deleted += 1
                logger.info(f"Deleted {bid}")
            else:
                errors += 1
                logger.error(f"Failed {bid} -> {err}")

    return deleted, errors


# ----------------------------------------------------------
# main
# ----------------------------------------------------------
def main():

    parser = argparse.ArgumentParser(description="OCI Backup Cleanup Tool")

    parser.add_argument("-c", "--compartment-id", required=True)
    parser.add_argument("-k", "--keep", required=True, type=int)

    parser.add_argument("--boot-only", action="store_true")
    parser.add_argument("--block-only", action="store_true")

    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--sleep-between", type=float, default=0.5)
    parser.add_argument("--workers", type=int, default=3)

    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--profile", default=DEFAULT_PROFILE)

    parser.add_argument("--log-level", default="INFO")
    parser.add_argument("--log-file")

    args = parser.parse_args()

    if args.boot_only and args.block_only:
        parser.error("Cannot use both --boot-only and --block-only")

    logger = setup_logging(args.log_level, args.log_file)

    logger.info("Starting OCI backup cleanup")

    try:

        client = init_client(args.config, args.profile)

        process_boot = not args.block_only
        process_block = not args.boot_only

        total_deleted = 0
        total_errors = 0

        if process_boot:
            logger.info("Checking boot volume backups...")
            boot_backups = list_backups(client, args.compartment_id, True)
            grouped = group_by_volume(boot_backups, True)

            d, e = cleanup(
                client, grouped, args.keep,
                args.dry_run, args.workers,
                True, args.sleep_between, logger
            )

            total_deleted += d
            total_errors += e

        if process_block:
            logger.info("Checking block volume backups...")
            block_backups = list_backups(client, args.compartment_id, False)
            grouped = group_by_volume(block_backups, False)

            d, e = cleanup(
                client, grouped, args.keep,
                args.dry_run, args.workers,
                False, args.sleep_between, logger
            )

            total_deleted += d
            total_errors += e

        logger.info(f"Deleted: {total_deleted}")
        logger.info(f"Errors : {total_errors}")
        logger.info("Cleanup finished")

        sys.exit(1 if total_errors else 0)

    except ConfigFileNotFound:
        logger.error("OCI config file not found")
        sys.exit(1)

    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
        sys.exit(130)

    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
