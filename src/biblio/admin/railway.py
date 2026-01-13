import asyncio
import os
from typing import Any

import httpx

from src.biblio.config.config import RailwayService, get_parser, load_env
from src.biblio.config.logger import setup_logger

RAILWAY_GRAPHQL_ENDPOINT = "https://backboard.railway.app/graphql/v2"
_DEFAULT_TIMEOUT = 20.0
SERVICE_LIST = [s.value for s in RailwayService]


class RailwayError(RuntimeError):
    pass


async def _post(query: str, variables: dict[str, Any]) -> dict[str, Any]:
    headers = {
        "Project-Access-Token": f"{os.getenv('RAILWAY_TOKEN')}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
        resp = await client.post(
            RAILWAY_GRAPHQL_ENDPOINT,
            json={"query": query, "variables": variables},
            headers=headers,
        )
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        raise RailwayError(str(data["errors"]))
    return data["data"]


async def list_deployments(
    service: str = "BOT",
) -> list[dict[str, Any]]:
    if service.upper() not in SERVICE_LIST:
        raise ValueError("Service not found!")

    service_id = os.getenv(f"RAILWAY_{service.upper()}_SERVICE_ID")
    if not service_id:
        raise ValueError("Service ID not configured!")
    if not os.getenv("RAILWAY_ENV_ID"):
        raise ValueError("Environment ID not configured!")

    query = """
    query Deployments($serviceId: String!, $environmentId: String!) {
      deployments(input: { serviceId: $serviceId, environmentId: $environmentId }) {
        edges { node { id status createdAt environmentId } }
      }
    }
    """
    data = await _post(
        query,
        {"serviceId": service_id, "environmentId": os.getenv("RAILWAY_ENV_ID")},
    )
    edges = data.get("deployments", {}).get("edges", [])
    return [edge["node"] for edge in edges if "node" in edge]


async def remove_deployment(deployment_id: str) -> str | None:
    query = """
    mutation Remove($id: String!) {
      deploymentRemove(id: $id)
    }
    """
    data = await _post(query, {"id": deployment_id})
    return data.get("deploymentRemove")


async def redeploy_deployment(deployment_id: str) -> dict[str, Any]:
    query = """
    mutation Redeploy($id: String!) {
      deploymentRedeploy(id: $id) { id status }
    }
    """
    data = await _post(query, {"id": deployment_id})
    return data.get("deploymentRedeploy")


async def restart_deployment(deployment_id: str) -> dict[str, Any]:
    query = """
    mutation Restart($id: String!) {
      deploymentRestart(id: $id) { id status }
    }
    """
    data = await _post(query, {"id": deployment_id})
    return data.get("deploymentRestart")


async def deploy_service(
    service: str = "BOT",
    commit_sha: str | None = None,
) -> str:
    if service.upper() not in SERVICE_LIST:
        raise ValueError("Service not found!")
    service_id = os.getenv(f"RAILWAY_{service.upper()}_SERVICE_ID")
    if not service_id:
        raise ValueError("Service ID not configured!")
    if not os.getenv("RAILWAY_ENV_ID"):
        raise ValueError("Environment ID not configured!")

    query = """
    mutation Deploy($serviceId: String!, $environmentId: String!, $commitSha: String) {
      serviceInstanceDeployV2(
        serviceId: $serviceId,
        environmentId: $environmentId,
        commitSha: $commitSha
      )
    }
    """
    data = await _post(
        query,
        {
            "serviceId": service_id,
            "environmentId": os.getenv("RAILWAY_ENV_ID"),
            "commitSha": commit_sha,
        },
    )
    return data.get("serviceInstanceDeployV2")


async def main():
    setup_logger()
    parser = get_parser()
    args = parser.parse_args()
    load_env(args.env)
    results = await list_deployments()
    print(results)


if __name__ == "__main__":
    asyncio.run(main())
