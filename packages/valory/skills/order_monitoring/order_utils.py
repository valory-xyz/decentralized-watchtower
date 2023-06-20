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
# pylint: disable=C0103

"""This module contains helpers for orders."""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from eth_abi.packed import encode_packed
from py_eth_sig_utils.eip712.encoding import create_struct_hash
from py_eth_sig_utils.utils import sha3
from web3 import Web3


ORDER_TYPE_FIELDS = [
    {"name": "sellToken", "type": "address"},
    {"name": "buyToken", "type": "address"},
    {"name": "receiver", "type": "address"},
    {"name": "sellAmount", "type": "uint256"},
    {"name": "buyAmount", "type": "uint256"},
    {"name": "validTo", "type": "uint32"},
    {"name": "appData", "type": "bytes32"},
    {"name": "feeAmount", "type": "uint256"},
    {"name": "kind", "type": "string"},
    {"name": "partiallyFillable", "type": "bool"},
    {"name": "sellTokenBalance", "type": "string"},
    {"name": "buyTokenBalance", "type": "string"},
]
CANCELLATION_TYPE_FIELDS = [{"name": "order_uid", "type": "bytes"}]
DOMAIN_FIELD_TYPES = {
    "name": "string",
    "version": "string",
    "chainId": "uint256",
    "verifyingContract": "address",
    "salt": "bytes32",
}
DOMAIN_FIELD_NAMES = ["name", "version", "chainId", "verifyingContract", "salt"]

# Define ORDER_TYPE_HASH
fields = [f"{field['type']} {field['name']}" for field in ORDER_TYPE_FIELDS]
ORDER_TYPE_HASH = Web3.keccak(text=f"Order({','.join(fields)})").hex()
ORDER_UID_LENGTH = 56
ZERO_ADDRESS = "0x" + "0" * 40


@dataclass
class ConditionalOrderParamsStruct:
    """Conditional order params dataclass."""

    handler: str
    salt: str
    staticInput: str


@dataclass
class Proof:
    """Proof dataclass."""

    merkleRoot: str
    path: List[str]


@dataclass
class ConditionalOrder:
    """Conditional order dataclass."""

    id: str
    params: ConditionalOrderParamsStruct
    proof: Optional[Proof]
    orders: Dict[str, int]
    composableCow: str
    offchainInput: Optional[bytes]


OrderStatus = {"SUBMITTED": 1, "FILLED": 2}


class OrderKind(Enum):
    """Enum for order kinds."""

    SELL = "sell"
    BUY = "buy"


class OrderBalance(Enum):
    """Enum for order balance types."""

    ERC20 = "erc20"
    EXTERNAL = "external"
    INTERNAL = "internal"


def timestamp(t: Union[int, datetime]) -> int:
    """Converts a datetime to a timestamp."""
    if isinstance(t, datetime):
        return int(t.timestamp())
    return t


def balance_to_string(balance: str) -> str:
    """Converts a balance type to a string."""
    if balance == "0x5a28e9363bb942b639270062aa6bb295f434bcdfc42c97267bf003f272060dc9":
        return OrderBalance.ERC20.value
    if balance == "0xabee3b73373acd583a130924aad6dc38cfdc44ba0555ba94ce2ff63980ea0632":
        return OrderBalance.EXTERNAL.value
    if balance == "0x4ac99ace14ee0a5ef932dc609df0943ab7ac16b7583634612f8dc35a4289a6ce":
        return OrderBalance.INTERNAL.value

    raise ValueError(f"Unknown balance type: {balance}")


def kind_to_string(kind: str) -> str:
    """Converts an order kind to a string."""
    if kind == "0xf3b277728b3fee749481eb3e0b3b48980dbbab78658fc419025cb16eee346775":
        return OrderKind.SELL.value
    if kind == "0x6ed88e868af0a1983e3886d5f3e95a2fafbd6c3450bc229e27342283dc429ccc":
        return OrderKind.BUY.value

    raise ValueError(f"Unknown kind: {kind}")


def normalize_order(order: Dict) -> Dict[str, Union[str, int, bool]]:
    """Normalizes an order to be used in the orderbook."""
    normalized_order = {
        **order,
        "sellTokenBalance": balance_to_string(order["sellTokenBalance"]),
        "buyTokenBalance": balance_to_string(order["sellTokenBalance"]),
        "receiver": order.get("receiver", None) or ZERO_ADDRESS,
        "validTo": timestamp(order["validTo"]),
        "appData": bytes.fromhex(order["appData"][2:]),
        "kind": kind_to_string(order["kind"]),
    }
    return normalized_order


def hash_domain(domain: Dict[str, Union[str, int]]) -> bytes:
    """Hashes domain"""
    domain_fields = []
    for name in domain:
        field_type = DOMAIN_FIELD_TYPES.get(name)
        if not field_type:
            raise ValueError(f"invalid typed-data domain key: {name!r}")
        domain_fields.append({"name": name, "type": field_type})

    domain_fields.sort(key=lambda field: DOMAIN_FIELD_NAMES.index(field["name"]))
    domain_hash = create_struct_hash(
        "EIP712Domain",
        domain,
        {"EIP712Domain": domain_fields},
    )
    return domain_hash


def hash_order(order: Dict[str, Any]) -> bytes:
    """Hashes order"""
    normalized_order = normalize_order(order)
    order_hash = create_struct_hash(
        "Order", normalized_order, {"Order": ORDER_TYPE_FIELDS}
    )
    return order_hash


class OrderUidParams:  # pylint: disable=too-few-public-methods
    """Order UID params"""

    def __init__(
        self, order_digest: bytes, owner: str, valid_to: Union[int, datetime]
    ) -> None:
        """Initializes OrderUidParams"""
        self.order_digest = order_digest
        self.owner = owner
        self.valid_to = valid_to


def compute_order_uid(
    domain: Dict[str, Union[str, int]], order: Dict[str, Any], owner: str
) -> bytes:
    """Computes order UID from order and owner"""
    domain_hash = hash_domain(domain)
    order_hash = hash_order(order)
    full_hash = sha3(
        bytes.fromhex("19") + bytes.fromhex("01") + domain_hash + order_hash
    )
    types = ["bytes32", "address", "uint32"]
    order_uid = encode_packed(types, [full_hash, owner, order["validTo"]])
    return "0x" + order_uid.hex()


def extract_order_uid_params(order_uid: bytes) -> OrderUidParams:
    """Extracts order UID params from order UID"""
    if len(order_uid) != ORDER_UID_LENGTH:
        raise ValueError("Invalid order UID length")
    order_digest = order_uid[:32]
    owner = Web3.toChecksumAddress(order_uid[32:52].hex())
    valid_to = int.from_bytes(order_uid[52:], byteorder="big")
    return OrderUidParams(order_digest, owner, valid_to)
