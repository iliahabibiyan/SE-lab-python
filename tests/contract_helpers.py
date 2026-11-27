import pathlib

import yaml
from jsonschema import Draft202012Validator

CONTRACT_PATH = pathlib.Path(__file__).resolve().parent.parent / "openapi" / "account.yaml"
CONTRACT = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))


def resolve(node):
    """Return `node` with every $ref replaced by what it points to (the contract has no recursive schemas)."""
    if isinstance(node, dict):
        if "$ref" in node:
            target = CONTRACT
            for part in node["$ref"][2:].split("/"):
                target = target[part]
            return resolve(target)
        return {key: resolve(value) for key, value in node.items()}
    if isinstance(node, list):
        return [resolve(item) for item in node]
    return node


def operation(operation_id: str) -> dict:
    for path_item in CONTRACT["paths"].values():
        for operation_data in path_item.values():
            if isinstance(operation_data, dict) and operation_data.get("operationId") == operation_id:
                return operation_data
    raise KeyError(operation_id)


def assert_matches_contract(response, operation_id: str, status: int | None = None) -> None:
    """The status code, the content type and the body of `response` must be declared for the operation."""
    if status is not None:
        assert response.status_code == status, response.text
    responses = operation(operation_id)["responses"]
    declared = responses.get(str(response.status_code))
    assert declared is not None, (
        f"{operation_id}: status {response.status_code} is not in the contract {sorted(responses)}"
    )
    content = resolve(declared).get("content", {})
    if not content:
        assert not response.content, f"{operation_id}: the contract says there is no body"
        return
    media_type = response.headers["content-type"].split(";")[0]
    assert media_type in content, f"{operation_id}: content type {media_type} is not in the contract {sorted(content)}"
    schema = content[media_type]["schema"]
    Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER).validate(response.json())