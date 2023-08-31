# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2023 Valory AG
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# ------------------------------------------------------------------------------
"""This module contains an implementation of py_eth_utils encoding."""


from eth_abi import encode

from packages.valory.skills.order_monitoring.sig_utils import utils


def encode_single(data_type: str, value) -> bytes:
    """Encode a single value."""
    return encode([data_type], [value])


def create_struct_definition(name: str, schema: list) -> str:
    """Create a struct definition."""
    schema_types = [
        f"{schema_type['type']} {schema_type['name']}" for schema_type in schema
    ]
    return f"{name}({','.join(schema_types)})"


def find_dependencies(name: str, types: dict, dependencies: set) -> None:
    """Find dependencies for a given name."""
    if name in dependencies:
        return
    schema = types.get(name)
    if not schema:
        return
    dependencies.add(name)
    for schema_type in schema:
        find_dependencies(schema_type["type"], types, dependencies)


def create_schema(name: str, types: dict) -> str:
    """Create a schema definition."""
    array_start = name.find("[")
    clean_name = name if array_start < 0 else name[:array_start]
    dependencies = set()
    find_dependencies(clean_name, types, dependencies)
    dependencies.discard(clean_name)
    dependency_definitions = [
        create_struct_definition(dependency, types[dependency])
        for dependency in sorted(dependencies)
        if types.get(dependency)
    ]
    return create_struct_definition(clean_name, types[clean_name]) + "".join(
        dependency_definitions
    )


def create_schema_hash(name: str, types: dict) -> bytes:
    """Create a schema hash."""
    return encode_single("bytes32", utils.sha3(create_schema(name, types)))


def encode_value(data_type: str, value, types: dict) -> bytes:
    """Encode a value based on its data type."""
    if data_type == "string":
        return encode_single("bytes32", utils.sha3(value))
    elif data_type == "bytes":
        return encode_single("bytes32", utils.sha3(utils.scan_bin(value)))
    elif types.get(data_type):
        return encode_single(
            "bytes32", utils.sha3(encode_data(data_type, value, types))
        )
    elif data_type.endswith("]"):
        array_type = data_type[: data_type.index("[")]
        return encode_single(
            "bytes32",
            utils.sha3(
                b"".join(
                    [
                        encode_data(array_type, array_value, types)
                        for array_value in value
                    ]
                )
            ),
        )
    else:
        return encode_single(data_type, value)


def encode_data(name: str, data, types: dict) -> bytes:
    """Encode data based on the provided name and types."""
    return create_schema_hash(name, types) + b"".join(
        [
            encode_value(schema_type["type"], data[schema_type["name"]], types)
            for schema_type in types[name]
        ]
    )


def create_struct_hash(name: str, data, types: dict) -> bytes:
    """Create a hash for a structured data."""
    return utils.sha3(encode_data(name, data, types))


def encode_typed_data(data: dict) -> bytes:
    """Encode typed data."""
    assert data
    types = data.get("types")
    assert types
    domain_schema = types.get("EIP712Domain")
    assert domain_schema and type(domain_schema) is list

    primary_type = data.get("primaryType")
    assert primary_type
    domain = data.get("domain")
    assert domain
    # TODO: Check domain object against schema
    message = data.get("message")
    assert message

    domain_hash = create_struct_hash("EIP712Domain", domain, types)
    message_hash = create_struct_hash(primary_type, message, types)
    return utils.sha3(
        bytes.fromhex("19") + bytes.fromhex("01") + domain_hash + message_hash
    )
