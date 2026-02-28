# OCI Tenancy Resource Inventory Export Tool

A production-ready Python utility to export all Oracle Cloud Infrastructure (OCI) resources across a tenancy into a structured CSV report.

This tool uses the OCI Python SDK and Resource Search API to generate a complete resource inventory including compartment mapping and tag information.

---

## Features

- Exports all resources across tenancy
- Maps resources to compartment names
- Supports lifecycle state filtering
- Optional compartment-level filtering
- Retry strategy enabled
- Pagination handling
- Logging (console + file)
- Timestamped CSV output
- JSON-safe tag export
- Production-grade error handling

---

## Architecture Overview

The script performs the following steps:

1. Loads OCI configuration profile
2. Fetches tenancy and all active compartments
3. Executes structured resource search query
4. Handles pagination automatically
5. Maps resources to compartment names
6. Exports detailed results into CSV format

---

##  Prerequisites

- Python 3.8+
- OCI CLI configured (`~/.oci/config`)

**Required IAM permissions:**

Allow group <group-name> to inspect all-resources in tenancy
Allow group <group-name> to read compartments in tenancy

---

##  Installation

Clone the repository:

```bash
git clone https://github.com/<your-username>/oci-tenancy-resource-inventory.git
cd oci-tenancy-resource-inventory

Install dependencies:

pip install -r oci

---

Usage
Run with default profile:

python oci_tenancy_inventory.py

Use specific profile:
python oci_tenancy_inventory.py --profile PROD

Filter by lifecycle state:
python oci_tenancy_inventory.py --lifecycle-state ACTIVE

Limit to a specific compartment:
python oci_tenancy_inventory.py --compartment-id ocid1.compartment.oc1...

Override region:
python oci_tenancy_inventory.py --region ap-mumbai-1

**Output**

The script generates a timestamped CSV file:

tenancy_resources_YYYYMMDD_HHMMSS.csv

**Columns included:**

resourceType
displayName
identifier (OCID)
compartmentName
compartmentId
region
timeCreated
lifecycleState
definedTags
freeformTags

Logs are written to:
oci_inventory.log

**Example Use Cases**

Governance & compliance reporting
Tag auditing
Security reviews
Cost visibility analysis
Resource inventory documentation
Cloud environment assessment

