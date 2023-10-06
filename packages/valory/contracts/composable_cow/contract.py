# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2023Valory AG
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

"""This module contains the class to connect to an Gnosis Safe contract."""
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional, Dict, List, Tuple

from aea.common import JSONLike
from aea.configurations.base import PublicId
from aea.contracts.base import Contract
from aea.crypto.base import LedgerApi

PUBLIC_ID = PublicId.from_str("valory/composable_cow:0.1.0")

_logger = logging.getLogger(
    f"aea.packages.{PUBLIC_ID.author}.contracts.{PUBLIC_ID.name}.contract"
)


TWAP_STRUCT_ABI = [
    ('address', 'sellToken'),
    ('address', 'buyToken'),
    ('address', 'receiver'),
    ('uint256', 'partSellAmount'),
    ('uint256', 'minPartLimit'),
    ('uint256', 't0'),
    ('uint256', 'n'),
    ('uint256', 't'),
    ('uint256', 'span'),
    ('bytes32', 'appData'),
]


@dataclass
class TWAPData:
    sellToken: str
    buyToken: str
    receiver: str
    partSellAmount: int
    minPartLimit: int
    t0: int
    n: int
    t: int
    span: int
    appData: bytes


class CallType(Enum):
    """Call type."""

    EVENT_PROCESSING = "event_processing"
    GET_TRADEABLE_ORDER = "tradable_order"


class OrderBalance(Enum):
    """Order balance."""

    ERC20 = "erc20"
    EXTERNAL = "external"
    INTERNAL = "internal"


class ComposableCowContract(Contract):
    """The ComposableCow contract."""

    contract_id = PUBLIC_ID

    @classmethod
    def get_raw_transaction(
        cls, ledger_api: LedgerApi, contract_address: str, **kwargs: Any
    ) -> Optional[JSONLike]:
        """Get the Safe transaction."""
        raise NotImplementedError

    @classmethod
    def get_raw_message(
        cls, ledger_api: LedgerApi, contract_address: str, **kwargs: Any
    ) -> Optional[bytes]:
        """Get raw message."""
        raise NotImplementedError

    @classmethod
    def get_state(
        cls, ledger_api: LedgerApi, contract_address: str, **kwargs: Any
    ) -> Optional[JSONLike]:
        """Get state."""
        raise NotImplementedError

    @staticmethod
    def parse_order_data(order_data: Tuple) -> Dict[str, Any]:
        """Parse order data."""
        return {
            "sellToken": order_data[0],
            "buyToken": order_data[1],
            "receiver": order_data[2],
            "sellAmount": order_data[3],
            "buyAmount": order_data[4],
            "validTo": order_data[5],
            "appData": "0x" + order_data[6].hex(),
            "feeAmount": order_data[7],
            "kind": "0x" + order_data[8].hex(),
            "partiallyFillable": order_data[9],
            "sellTokenBalance": "0x" + order_data[10].hex(),
            "buyTokenBalance": "0x" + order_data[11].hex(),
        }

    @classmethod
    def get_tradeable_order(
        cls,
        ledger_api: LedgerApi,
        contract_address: str,
        orders: List[Dict[str, Any]],
    ) -> Optional[JSONLike]:
        """Get tradeable order."""
        tradeable_orders: List[Dict[str, Any]] = []
        drop_orders: List[Dict[str, Any]] = []
        for order in orders:
            try:
                static_input = order["params"][2]
                composable_cow = order["composableCow"]
                twap_data = cls.decode_twap_struct(
                    ledger_api,
                    static_input,
                )
                should_drop_order = cls.should_drop_order(
                    ledger_api,
                    composable_cow,
                    order,
                    twap_data,
                )
                if should_drop_order:
                    drop_orders.append(order)
                    continue
                instance = cls.get_instance(ledger_api, order["composableCow"])
                (
                    order_data,
                    signature,
                ) = instance.functions.getTradeableOrderWithSignature(
                    order["owner"],
                    order["params"],
                    order["offchainInput"],
                    order["proof"],
                ).call()
                tradeable_orders.append(
                    {
                        **cls.parse_order_data(order_data),
                        "signingScheme": "eip1271",
                        "signature": "0x" + signature.hex(),
                        "from": order["owner"],
                        "id": order["id"],
                        "chainId": ledger_api.api.eth.chain_id,
                    }
                )
            except Exception as e:
                _logger.info(f"Order {order} not tradeable : {e}")

        return dict(data=dict(tradeable_orders=tradeable_orders, drop_orders=drop_orders), type=CallType.GET_TRADEABLE_ORDER.value)

    @staticmethod
    def decode_twap_struct(
        ledger_api: LedgerApi,
        static_input: bytes,
    ) -> Optional[TWAPData]:
        """Decode twap struct."""
        [
            sellToken,
            buyToken,
            receiver,
            partSellAmount,
            minPartLimit,
            t0,
            n,
            t,
            span,
            appData,
        ] = ledger_api.api.codec.decode_abi(TWAP_STRUCT_ABI, static_input)
        return TWAPData(
            sellToken=sellToken,
            buyToken=buyToken,
            receiver=receiver,
            partSellAmount=partSellAmount,
            minPartLimit=minPartLimit,
            t0=t0,
            n=n,
            t=t,
            span=span,
            appData=appData,
        )

    @classmethod
    def get_start_timestamp(cls, ledger_api: LedgerApi, contract_address: str, order: Dict[str, Any], data: TWAPData) -> int:
        """Get start timestamp."""
        if data.span != 0:
            return data.t0

        contract = cls.get_instance(ledger_api, contract_address)
        start_timestamp_hex = contract.functions.cabinet(order["owner"], order["id"]).call()
        start_timestamp = ledger_api.api.codec.decode_abi(['unit256'], start_timestamp_hex)[0]
        return start_timestamp

    @classmethod
    def get_end_timestamp(cls, ledger_api: LedgerApi, contract_address: str, order: Dict[str, Any], data: TWAPData) -> int:
        """Get start timestamp."""
        start_timestamp = cls.get_start_timestamp(ledger_api, contract_address, order, data)
        if data.span == 0:
            return start_timestamp + data.n * data.t

        return start_timestamp + (data.n - 1) * data.t + data.span

    @classmethod
    def should_drop_order(
        cls,
        ledger_api: LedgerApi,
        contract_address: str,
        order: Dict[str, Any],
        data: TWAPData,
    ):
        block = ledger_api.api.eth.get_block("latest")
        block_timestamp = block.timestamp
        start_timestamp = cls.get_start_timestamp(ledger_api, contract_address, order, data)
        end_timestamp = cls.get_end_timestamp(ledger_api, contract_address, order, data)

        if start_timestamp > block_timestamp:
            # The start time hasn't started
            return False

        if block_timestamp >= end_timestamp:
            # The order has expired
            return True

        return False

    @classmethod
    def process_order_events(
        cls, ledger_api: LedgerApi, contract_address: str, tx_hash: str
    ) -> JSONLike:
        """Process order events"""
        contract = cls.get_instance(ledger_api, contract_address)
        receipt = ledger_api.api.eth.get_transaction_receipt(tx_hash)
        conditional_orders = [
            {**event.get("args", {}), "composableCow": event.address}
            for event in contract.events.ConditionalOrderCreated().process_receipt(
                receipt
            )
        ]
        merkle_root_set = [
            {**event.get("args", {}), "composableCow": event.address}
            for event in contract.events.MerkleRootSet().process_receipt(receipt)
        ]
        data = {
            "conditional_orders": conditional_orders,
            "merkle_root_set": merkle_root_set,
        }
        return dict(data=data, type=CallType.EVENT_PROCESSING.value)
