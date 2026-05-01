import asyncio
from pprint import pprint

from dotenv import load_dotenv

from app.services.evidence.evidence_api_builder import EvidenceApiBuilder


async def main():
    load_dotenv()

    builder = EvidenceApiBuilder()

    payload = await builder.build_api_snapshot(
        municipality_id="TLX-APZ",
        municipality_name="Apizaco",
        lat=19.4167,
        lon=-98.1333,
        denue_radius_m=1000,
    )

    print("\n=== ECONOMIC DATA ===")
    pprint(payload["economic_data"])

    print("\n=== INFRASTRUCTURE DATA ===")
    pprint(payload["infrastructure_data"])

    print("\n=== SOURCES USED ===")
    pprint(payload["sources_used"])

    print("\n=== SOURCES FAILED ===")
    pprint(payload["sources_failed"])


if __name__ == "__main__":
    asyncio.run(main())