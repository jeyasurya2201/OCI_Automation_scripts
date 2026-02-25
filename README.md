OCI Backup Cleanup Script

**Overview**

This is a small Python utility I created to clean up old Boot Volume and Block Volume backups in an Oracle Cloud Infrastructure (OCI) compartment.

In long-running environments, backups keep accumulating over time. Even when backup policies are configured correctly, older backups remain and gradually increase storage usage and cost. Manually checking and deleting them is time-consuming, especially across multiple volumes.

This script helps automate that process by keeping only the most recent backups per volume and removing the older ones safely.

**What the Script Does**

Scans all Boot Volume backups in a compartment

Scans all Block Volume backups in a compartment

Groups backups by their parent volume

Keeps only the newest N backups per volume

Deletes older backups automatically

Supports dry-run mode to preview changes

Includes retry handling and optional delay to avoid OCI throttling

Allows filtering for boot-only or block-only cleanup

Supports logging to console or file

**Requirements**

Python 3.8 or later

OCI Python SDK

Install the SDK:

pip install oci

You also need a valid OCI CLI-style config file, usually located at:

~/.oci/config

Example config:

[DEFAULT]
tenancy=<tenancy_ocid>
user=<user_ocid>
fingerprint=<fingerprint>
key_file=<path_to_private_key>
region=<region>
Required IAM Permissions

The user running this script must be allowed to manage backups in the target compartment.

**Example policy:**

Allow group CloudAdmins to manage volume-backups in compartment MyCompartment
Allow group CloudAdmins to manage boot-volume-backups in compartment MyCompartment

Command Line Examples

The script scans all Boot and Block Volume backups inside the specified compartment and removes older backups based on the retention value you provide.

Below are some practical examples showing how I typically run it in different situations.

Basic Usage

**Preview cleanup (recommended first):**

This runs in dry-run mode and shows which backups would be removed while keeping the latest 3 backups per volume.

python oci_backup_cleanup.py -c ocid1.compartment.oc1..xxxx -k 3 --dry-run

**Run actual cleanup:**

Deletes older backups and keeps only the newest 5 backups per volume.

python oci_backup_cleanup.py -c ocid1.compartment.oc1..xxxx -k 5
Using a Custom OCI Config or Profile

By default, the script reads credentials from:

~/.oci/config   (profile: DEFAULT)

If you need to use another config file or profile:

Custom config file (DEFAULT profile):

python oci_backup_cleanup.py \
-c ocid1.compartment.oc1..xxxx \
-k 5 \
--config /home/ubuntu/.oci/prod_config

Custom config file with specific profile:

python oci_backup_cleanup.py \
-c ocid1.compartment.oc1..xxxx \
-k 5 \
--config /home/ubuntu/.oci/prod_config \
--profile PROD

The config file must follow the standard OCI CLI format and include:

tenancy

user

fingerprint

key_file

region

Controlling API Throttling

If the compartment contains many backups, OCI may throttle delete requests.
You can slow the script slightly for smoother execution.

Sleep 1 second between deletes:

python oci_backup_cleanup.py \
-c ocid1.compartment.oc1..xxxx \
-k 4 \
--sleep-between 1

More conservative cleanup with debug logging enabled:

python oci_backup_cleanup.py \
-c ocid1.compartment.oc1..xxxx \
-k 2 \
--sleep-between 2 \
--log-level DEBUG
Processing Only Specific Backup Types

Sometimes you may want to clean only one type of backup.

**Only Boot Volume backups:**

python oci_backup_cleanup.py \
-c ocid1.compartment.oc1..xxxx \
-k 3 \
--boot-only

**Only Block Volume backups:**

python oci_backup_cleanup.py \
-c ocid1.compartment.oc1..xxxx \
-k 3 \
--block-only
Writing Logs to a File

**To keep a record of what was deleted (useful for auditing or troubleshooting):**

python oci_backup_cleanup.py \
-c ocid1.compartment.oc1..xxxx \
-k 3 \
--sleep-between 0.5 \
--log-level INFO \
--log-file /var/log/oci_backup_cleanup.log

**Safety Notes**

Only backups in AVAILABLE state are processed

The script always keeps at least one newest backup per volume

Use --dry-run before first execution in a new environment

Consider starting with a small compartment for testing

**Automation (Cron)**

Run cleanup daily at 1:30 AM:

30 1 * * * /usr/bin/python3 /scripts/oci_backup_cleanup.py -c <compartment_ocid> -k 5 >> /var/log/oci_cleanup.log 2>&1

**Final Note**

This script is meant to simplify routine backup maintenance in OCI and avoid unnecessary storage growth.
Feel free to adjust the retention value or schedule it through automation depending on your environment.
