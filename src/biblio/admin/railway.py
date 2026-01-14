import asyncio
import os
from typing import Any

import httpx

from src.biblio.config.config import get_parser, load_env
from src.biblio.config.logger import setup_logger

RAILWAY_GRAPHQL_ENDPOINT = "https://backboard.railway.app/graphql/v2"
_DEFAULT_TIMEOUT = 20.0


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


async def list_environments() -> list[dict[str, str]]:
    project_id = os.getenv("RAILWAY_PROJECT_ID")
    if not project_id:
        raise ValueError("Project ID not configured!")
    query = """
    query Envs($projectId: String!) {
      environments(projectId: $projectId) {
        edges { node { id name } }
      }
    }
    """
    data = await _post(query, {"projectId": project_id})
    edges = data.get("environments", {}).get("edges", [])
    return [
        {"id": edge["node"]["id"], "name": edge["node"]["name"]}
        for edge in edges
        if "node" in edge and "id" in edge["node"]
    ]


async def list_services() -> list[dict[str, str]]:
    project_id = os.getenv("RAILWAY_PROJECT_ID")
    if not project_id:
        raise ValueError("Project ID not configured!")
    query = """
    query ProjectServices($projectId: String!) {
      project(id: $projectId) {
        services { edges { node { id name icon } } }
      }
    }
    """
    data = await _post(query, {"projectId": project_id})
    edges = data.get("project", {}).get("services", {}).get("edges", [])
    return [
        {"id": edge["node"]["id"], "name": edge["node"]["name"]}
        for edge in edges
        if "node" in edge and "id" in edge["node"]
    ]


async def list_deployments(
    service_id: str,
    environment_id: str,
) -> list[dict[str, Any]]:
    query = """
    query Deployments($serviceId: String!, $environmentId: String!) {
      deployments(input: { serviceId: $serviceId, environmentId: $environmentId }) {
        edges { node { id status createdAt environmentId } }
      }
    }
    """
    data = await _post(
        query,
        {
            "serviceId": service_id,
            "environmentId": environment_id,
        },
    )
    edges = data.get("deployments", {}).get("edges", [])
    return [edge["node"] for edge in edges if "node" in edge]


async def get_last_deployment_id(
    service_id: str,
    environment_id: str,
) -> dict[str, str] | None:
    deployments = await list_deployments(service_id, environment_id)
    if not deployments:
        return None
    latest = max(deployments, key=lambda d: d.get("createdAt", ""))
    return {"id": latest.get("id"), "created_at": latest.get("createdAt")}


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
    service_id: str,
    environment_id: str,
    commit_sha: str | None = None,
) -> str:
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
            "environmentId": environment_id,
            "commitSha": commit_sha,
        },
    )
    return data.get("serviceInstanceDeployV2")


async def main():
    setup_logger()
    parser = get_parser()
    args = parser.parse_args()
    load_env(args.env)
    # results = await remove_deployment("b1822a76-5678-432c-984f-6397d1156316")
    # results = await list_deployments("bot")
    # results = await get_last_deployment_id("bot")
    # results = await deploy_service("bot")
    results = await list_services()
    print(results)


if __name__ == "__main__":
    asyncio.run(main())
