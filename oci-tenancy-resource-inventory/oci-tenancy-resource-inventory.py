#!/usr/bin/env python3

import oci
import csv
import argparse
import logging
import json
import sys
from datetime import datetime
from oci.pagination import list_call_get_all_results

# ==========================================================
# Logging Configuration
# ==========================================================
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("oci_inventory.log")
        ]
    )


# ==========================================================
# Argument Parser
# ==========================================================
def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Export OCI Tenancy Resources to CSV"
    )

    parser.add_argument(
        "--profile",
        default="DEFAULT",
        help="OCI config profile name (default: DEFAULT)"
    )

    parser.add_argument(
        "--compartment-id",
        help="Optional: Limit search to a specific compartment OCID"
    )

    parser.add_argument(
        "--lifecycle-state",
        help="Optional: Filter by lifecycle state (e.g., ACTIVE)"
    )

    parser.add_argument(
        "--region",
        help="Optional: Override region from config"
    )

    return parser.parse_args()


# ==========================================================
# Initialize OCI Clients
# ==========================================================
def initialize_clients(profile, region_override=None):
    config = oci.config.from_file("~/.oci/config", profile)

    if region_override:
        config["region"] = region_override

    retry_strategy = oci.retry.DEFAULT_RETRY_STRATEGY

    search_client = oci.resource_search.ResourceSearchClient(
        config,
        retry_strategy=retry_strategy
    )

    identity_client = oci.identity.IdentityClient(
        config,
        retry_strategy=retry_strategy
    )

    return config, search_client, identity_client


# ==========================================================
# Fetch Compartments
# ==========================================================
def fetch_compartments(identity_client, tenancy_id):
    logging.info("Fetching compartments...")

    compartment_map = {}

    tenancy = identity_client.get_tenancy(tenancy_id).data
    compartment_map[tenancy.id] = tenancy.name

    compartments = list_call_get_all_results(
        identity_client.list_compartments,
        tenancy_id,
        compartment_id_in_subtree=True
    ).data

    for comp in compartments:
        if comp.lifecycle_state == "ACTIVE":
            compartment_map[comp.id] = comp.name

    logging.info(f"Loaded {len(compartment_map)} compartments.")
    return compartment_map


# ==========================================================
# Search Resources
# ==========================================================
def search_resources(search_client, query):
    logging.info("Searching resources...")

    search_details = oci.resource_search.models.StructuredSearchDetails(
        type="Structured",
        query=query,
    )

    all_resources = []
    next_page = None

    while True:
        response = search_client.search_resources(
            search_details=search_details,
            limit=1000,
            page=next_page
        )

        all_resources.extend(response.data.items)
        next_page = response.headers.get("opc-next-page")

        if not next_page:
            break

    logging.info(f"Found {len(all_resources)} resources.")
    return all_resources


# ==========================================================
# Export to CSV
# ==========================================================
def export_to_csv(resources, compartment_map):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"tenancy_resources_{timestamp}.csv"

    logging.info(f"Exporting to {filename}")

    headers = [
        'resourceType',
        'displayName',
        'identifier',
        'compartmentName',
        'compartmentId',
        'region',
        'timeCreated',
        'lifecycleState',
        'definedTags',
        'freeformTags'
    ]

    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()

        for item in resources:
            comp_id = getattr(item, 'compartment_id', '')
            comp_name = compartment_map.get(comp_id, 'Unknown')

            writer.writerow({
                'resourceType': getattr(item, 'resource_type', ''),
                'displayName': getattr(item, 'display_name', ''),
                'identifier': getattr(item, 'identifier', ''),
                'compartmentName': comp_name,
                'compartmentId': comp_id,
                'region': getattr(item, 'region', ''),
                'timeCreated': str(getattr(item, 'time_created', '')),
                'lifecycleState': getattr(item, 'lifecycle_state', ''),
                'definedTags': json.dumps(getattr(item, 'defined_tags', {})),
                'freeformTags': json.dumps(getattr(item, 'freeform_tags', {}))
            })

    logging.info("Export completed successfully.")
    return filename


# ==========================================================
# Main
# ==========================================================
def main():
    setup_logging()
    args = parse_arguments()

    try:
        config, search_client, identity_client = initialize_clients(
            args.profile,
            args.region
        )

        tenancy_id = config["tenancy"]

        if args.compartment_id:
            query = f"query all resources where compartmentId = '{args.compartment_id}'"
        else:
            query = "query all resources"

        if args.lifecycle_state:
            query += f" && lifecycleState = '{args.lifecycle_state}'"

        compartment_map = fetch_compartments(identity_client, tenancy_id)

        resources = search_resources(search_client, query)

        if not resources:
            logging.warning("No resources found.")
            sys.exit(0)

        filename = export_to_csv(resources, compartment_map)

        logging.info(f"Report generated: {filename}")

    except Exception as e:
        logging.error(f"Error occurred: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
