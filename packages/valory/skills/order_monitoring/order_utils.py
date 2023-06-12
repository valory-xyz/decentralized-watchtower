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
"""This module contains helpers for orders."""
from dataclasses import dataclass
from typing import Union, Dict, List, Optional
from enum import Enum
from datetime import datetime

from eth_typing import HexStr
from py_eth_sig_utils.eip712.encoding import create_struct_hash
from web3 import Web3

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

    params: ConditionalOrderParamsStruct
    proof: Optional[Proof]
    orders: Dict[str, int]
    composableCow: str


OrderStatus = {
    'SUBMITTED': 1,
    'FILLED': 2
}


class Order:
    """Interface for orders."""
    def __init__(
        self,
        sell_token: str,
        buy_token: str,
        sell_amount: Union[int, str],
        buy_amount: Union[int, str],
        valid_to: Union[int, datetime],
        app_data: str,
        fee_amount: Union[int, str],
        kind: str,
        partially_fillable: bool,
        sell_token_balance: str = None,
        buy_token_balance: str = None,
        receiver: str = None
    ):
        """Initialize an order."""
        self.sell_token = sell_token
        self.buy_token = buy_token
        self.sell_amount = sell_amount
        self.buy_amount = buy_amount
        self.valid_to = valid_to
        self.app_data = app_data
        self.fee_amount = fee_amount
        self.kind = kind
        self.partially_fillable = partially_fillable
        self.sell_token_balance = sell_token_balance
        self.buy_token_balance = buy_token_balance
        self.receiver = receiver


class OrderCancellation:
    def __init__(self, order_uid: bytes):
        self.order_uid = order_uid


BUY_ETH_ADDRESS = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"


class OrderKind(Enum):
    """Enum for order kinds."""
    SELL = "sell"
    BUY = "buy"


class OrderBalance(Enum):
    """Enum for order balance types."""
    ERC20 = "erc20"
    EXTERNAL = "external"
    INTERNAL = "internal"


ORDER_TYPE_FIELDS = [
    {"name": "sell_token", "type": "address"},
    {"name": "buy_token", "type": "address"},
    {"name": "receiver", "type": "address"},
    {"name": "sell_amount", "type": "uint256"},
    {"name": "buy_amount", "type": "uint256"},
    {"name": "valid_to", "type": "uint32"},
    {"name": "app_data", "type": "bytes32"},
    {"name": "fee_amount", "type": "uint256"},
    {"name": "kind", "type": "string"},
    {"name": "partially_fillable", "type": "bool"},
    {"name": "sell_token_balance", "type": "string"},
    {"name": "buy_token_balance", "type": "string"},
]
CANCELLATION_TYPE_FIELDS = [{"name": "order_uid", "type": "bytes"}]


# Define ORDER_TYPE_HASH
fields = [f"{field['type']} {field['name']}" for field in ORDER_TYPE_FIELDS]
ORDER_TYPE_HASH = Web3.keccak(text=f"Order({','.join(fields)})").hex()


def timestamp(t: Union[int, datetime]) -> int:
    """Converts a datetime to a timestamp."""
    if isinstance(t, datetime):
        return int(t.timestamp())
    return t


def hashify(h: Union[bytes, int]) -> bytes:
    """Hashes a value."""
    if isinstance(h, int):
        return h.to_bytes(32, byteorder='big')
    return h.rjust(32, b'\x00')


def normalize_buy_token_balance(balance: OrderBalance) -> OrderBalance:
    """Normalizes the buy token balance."""
    if balance is None or balance == OrderBalance.ERC20 or balance == OrderBalance.EXTERNAL:
        return OrderBalance.ERC20
    if balance == OrderBalance.INTERNAL:
        return OrderBalance.INTERNAL
    raise ValueError(f"Invalid order balance {balance}")


def normalize_order(order: Order) -> Dict[str, Union[str, int, bool]]:
    """Normalizes an order to be used in the orderbook."""
    if order.receiver is None:
        raise ValueError("receiver cannot be None")
    normalized_order = {
        **order.__dict__,
        "sell_token_balance": order.sell_token_balance or OrderBalance.ERC20.value,
        "receiver": order.receiver or Web3.toChecksumAddress("0x" + "0" * 40),
        "valid_to": timestamp(order.valid_to),
        "app_data": hashify(order.app_data.encode()).hex(),
        "buy_token_balance": normalize_buy_token_balance(order.buy_token_balance.encode()).value,
    }
    return normalized_order


def hash_order(domain: Dict[str, Union[str, int]], order: Order) -> str:
    """Hashes order"""
    return create_struct_hash(
        domain,
        normalize_order(order),
        {"Order": {"type": "Order", "properties": {field["name"]: field["type"] for field in ORDER_TYPE_FIELDS}}},
    )


# Define hash_order_cancellation function
def hash_order_cancellation(domain: Dict[str, Union[str, int]], order_uid: bytes) -> str:
    """Hashes order cancellation"""
    return create_struct_hash(
        domain,
        {"OrderCancellation": {"type": "OrderCancellation", "properties": {"order_uid": "bytes"}}},
        {"order_uid": order_uid.hex()}
    )


ORDER_UID_LENGTH = 56


class OrderUidParams:
    """Order UID params"""

    def __init__(self, order_digest: bytes, owner: str, valid_to: Union[int, datetime]):
        """Initializes OrderUidParams"""
        self.order_digest = order_digest
        self.owner = owner
        self.valid_to = valid_to


def compute_order_uid(domain: Dict[str, Union[str, int]], order: Order, owner: str) -> bytes:
    """Computes order UID from order and owner"""
    order_uid_params = OrderUidParams(
        hash_order(domain, order).encode(),
        owner,
        order.valid_to,
    )
    return pack_order_uid_params(order_uid_params)


def pack_order_uid_params(params: OrderUidParams) -> bytes:
    """Packs order UID params into order UID"""
    return params.order_digest + Web3.toBytes(hexstr=HexStr(params.owner)) + params.valid_to.to_bytes(4, byteorder='big')


def extract_order_uid_params(order_uid: bytes) -> OrderUidParams:
    """Extracts order UID params from order UID"""
    if len(order_uid) != ORDER_UID_LENGTH:
        raise ValueError("Invalid order UID length")
    order_digest = order_uid[:32]
    owner = Web3.toChecksumAddress(order_uid[32:52].hex())
    valid_to = int.from_bytes(order_uid[52:], byteorder='big')
    return OrderUidParams(order_digest, owner, valid_to)
