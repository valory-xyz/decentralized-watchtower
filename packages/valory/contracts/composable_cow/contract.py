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
            "appData": '0x' + order_data[6].hex(),
            "feeAmount": order_data[7],
            "kind": '0x' + order_data[8].hex(),
            "partiallyFillable": order_data[9],
            "sellTokenBalance": '0x' + order_data[10].hex(),
            "buyTokenBalance": '0x' + order_data[11].hex(),
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
        for order in orders:
            try:
                instance = cls.get_instance(ledger_api, order["composableCow"])
                order_data, signature = instance.functions.getTradeableOrderWithSignature(
                    order["owner"],
                    order["params"],
                    order["offchainInput"],
                    order["proof"],
                ).call()
                tradeable_orders.append(
                    {
                        **cls.parse_order_data(order_data),
                        "signingScheme": "eip1271",
                        "signature": '0x' + signature.hex(),
                        "from": order["owner"],
                        "id": order["id"],
                        "chainId": ledger_api.api.eth.chain_id,
                    }
                )
            except Exception as e:
                _logger.info(f"Order {order} not tradeable : {e}")

        return dict(data=tradeable_orders, type=CallType.GET_TRADEABLE_ORDER.value)

    @classmethod
    def process_order_events(
        cls,
        ledger_api: LedgerApi,
        contract_address: str,
        tx_hash: str
    ) -> JSONLike:
        """Process order events"""
        contract = cls.get_instance(ledger_api, contract_address)
        receipt = ledger_api.api.eth.getTransactionReceipt(tx_hash)
        conditional_orders = [
            {**event.get("args", {}), "composableCow": event.address}
            for event in contract.events.ConditionalOrderCreated().processReceipt(receipt)
        ]
        merkle_root_set = [
            {**event.get("args", {}), "composableCow": event.address}
            for event in contract.events.MerkleRootSet().processReceipt(receipt)
        ]
        data = {
            "conditional_orders": conditional_orders,
            "merkle_root_set": merkle_root_set
        }
        return dict(data=data, type=CallType.EVENT_PROCESSING.value)
