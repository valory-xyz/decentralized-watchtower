# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2023 Valory AG
#   Copyright 2023 eightballer
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

"""This package contains a scaffold of a handler."""

import json
import time
from typing import Dict, Optional, List

from aea.protocols.base import Message
from aea.skills.base import Handler
from web3 import Web3
from web3.types import TxReceipt

from packages.fetchai.protocols.default.message import DefaultMessage

# partial orders are orders we do not have the full information for
# a partial order becomes (a full) order and is ready to be processed
PARTIAL_ORDERS = "partial_orders"
ORDERS = "orders"
DISCONNECTION_POINT = "disconnection_point"


class WebSocketHandler(Handler):
    """This class scaffolds a handler."""

    SUPPORTED_PROTOCOL = DefaultMessage.protocol_id
    w3: Web3 = None
    contract = None

    def __init__(self, **kwargs) -> None:
        self.websocket_provider = kwargs.pop("websocket_provider")
        self.contract_to_monitor = kwargs.pop("contract_to_monitor")
        super().__init__(**kwargs)

    def setup(self) -> None:
        """Implement the setup."""
        self.context.shared_state[PARTIAL_ORDERS] = []
        self.context.shared_state[ORDERS] = []
        self.context.shared_state[DISCONNECTION_POINT] = None
    @property
    def partial_orders(self) -> List[Dict[str, Dict]]:
        """Get partial orders."""
        return self.context.shared_state[PARTIAL_ORDERS]

    @property
    def orders(self) -> List[Dict[str, Dict]]:
        """Get orders."""
        return self.context.shared_state[ORDERS]

    def handle(self, message: Message) -> None:
        """
        Implement the reaction to an envelope.

        :param message: the message
        """
        self.context.logger.info(f"Received message: {message}")
        data = json.loads(message.content)
        if set(data.keys()) == {"id", "result", "jsonrpc"}:
            self.context.logger.info(f"Received response: {data}")
            return

        self.context.logger.info("Extracting data")
        tx_hash = data["params"]["result"]["transactionHash"]
        self._get_contract_events(tx_hash)

    def _get_contract_events(self, tx_hash: str):
        """Get contract events."""
        try:
            tx_receipt: TxReceipt = self.w3.eth.get_transaction_receipt(tx_hash)
            self.context.shared_state[DISCONNECTION_POINT] = tx_receipt["blockNumber"]
            rich_logs = self.contract.events.Request().processReceipt(tx_receipt)  # type: ignore
            return dict(rich_logs[0]["args"]), False

        except Exception as exc:  # pylint: disable=W0718
            self.context.logger.error(
                f"An exception occurred while trying to get the transaction arguments for {tx_hash}: {exc}"
            )
            return {}, True

    def _process_tx(self, tx_hash: str) -> Dict[str, List[Dict[str]]]:
        """Get the relevant events out of the transaction."""
        # TODO: send to ComposableCowContract for processing via ledger conn
        dummy_response = {
            "conditional_orders": [],
            "merkle_root_set": [],
        }

    def _add_contract(self, owner: str, params: Dict, proof: Optional[Dict], composable_cow: str):
        """Update contracts."""
        exists = False
        for order in self.orders:
            if order['owner'] == owner and order['params'] == params:
                exists = True
                break
        if not exists:
            self.orders.append({
                'owner': owner,
                'params': params,
                'proof': proof,
                'composableCow': composable_cow
            })

