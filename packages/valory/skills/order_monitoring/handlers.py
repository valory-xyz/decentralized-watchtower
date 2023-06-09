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
from dataclasses import dataclass
from typing import Dict, Optional, List, cast, Any

from aea.protocols.base import Message
from aea.skills.base import Handler
from web3 import Web3
from web3.types import TxReceipt

from packages.fetchai.protocols.default.message import DefaultMessage
from packages.valory.contracts.composable_cow.contract import ComposableCowContract, CallType
from packages.valory.protocols.contract_api import ContractApiMessage
from packages.valory.connections.ledger.connection import (
    PUBLIC_ID as LEDGER_CONNECTION_PUBLIC_ID,
)

# partial orders are orders we do not have the full information for
# a partial order becomes (a full) order and is ready to be processed
PARTIAL_ORDERS = "partial_orders"
ORDERS = "orders"
DISCONNECTION_POINT = "disconnection_point"

LEDGER_API_ADDRESS = str(LEDGER_CONNECTION_PUBLIC_ID)


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
        self.context.shared_state[PARTIAL_ORDERS] = {}
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

    def _process_tx(self, tx_hash: str) -> None:
        """Get the relevant events out of the transaction."""
        contract_api_msg, contract_api_dialogue = self.context.contract_api_dialogues.create(
            performative=ContractApiMessage.Performative.GET_STATE,
            contract_address=self.contract_to_monitor,
            contract_id=str(ComposableCowContract.contract_id),
            contract_callable="process_order_events",
            tx_hash=tx_hash,
            counterparty=LEDGER_API_ADDRESS,
            ledger_id=self.context.default_ledger_id,
        )
        self.context.outbox.put_message(message=contract_api_msg)


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


class ContractHandler(Handler):
    """Contract API message handler."""

    SUPPORTED_PROTOCOL = ContractApiMessage.protocol_id

    @property
    def orders(self) -> Dict[str, List[ConditionalOrder]]:
        """Get partial orders."""
        return self.context.shared_state[PARTIAL_ORDERS]

    def handle(self, message: Message) -> None:
        """
        Implement the reaction to a contract message.

        :param message: the message
        """
        self.context.logger.info(f"Received message: {message}")
        contract_api_msg = cast(ContractApiMessage, message)
        if contract_api_msg.performative != ContractApiMessage.Performative.STATE:
            self.context.logger.warning(
                f"Contract API Message performative not recognized: {contract_api_msg.performative}"
            )
            return

        body = contract_api_msg.state.body
        call_type = body.get('type', None)
        data = body.get('data', {})
        if call_type == CallType.EVENT_PROCESSING.value:
            self._handle_event_processing(data)

        if call_type == CallType.GET_TRADEABLE_ORDER.value:
            self._handle_get_tradeable_order(data)


    def _handle_get_tradeable_order(self, data: Dict[str, Any]) -> None:
        """Handle get tradeable order."""
        order = data.get('order', None)
        if order is None:
            return

        order_id = order['id']
        self._add_order(order_id, order)

    def _handle_event_processing(self, events: Dict[str, Any]) -> None:
        """Handle event processing."""
        conditional_orders = events.get('conditional_orders', [])
        merkle_root_set_events = events.get('merkle_root_set', [])
        for conditional_order in conditional_orders:
            self._add_contract(
                conditional_order['owner'],
                conditional_order['params'],
                conditional_order['proof'],
                conditional_order['composableCow']
            )

        for merkle_root_set in merkle_root_set_events:
            self._flush_contracts(
                merkle_root_set['owner'],
                merkle_root_set['merkleRoot'],
            )
            for order in merkle_root_set['orders']:
                self._add_contract(
                    merkle_root_set['owner'],
                    order['params'],
                    Proof(
                        merkle_root_set['merkleRoot'],
                        order['path']
                    ),
                    order['address'],
                )

    def _add_contract(
        self,
        owner: str,
        params: ConditionalOrderParamsStruct,
        proof: Optional[Proof],
        composable_cow: str,
    ) -> None:
        """Add a conditional order to the registry."""
        if owner in self.orders:
            conditional_orders = self.orders[owner]
            self.context.logger.info(f"Adding conditional order {params} to already existing owner {owner}")
            exists = False
            # Iterate over the conditionalOrder to make sure that the params are not already in the registry
            for conditional_order in conditional_orders:
                # Check if the params are in the conditionalOrder
                if conditional_order.params == params:
                    exists = True
                    break

            # If the params are not in the conditionalOrder, add them
            # we essentially use the params as identifier for the conditional order
            if not exists:
                conditional_order = ConditionalOrder(
                    params=params,
                    proof=proof,
                    orders={},
                    composableCow=composable_cow
                )
                conditional_orders.append(conditional_order)

        else:
            # this is the first order for this owner
            self.context.logger.info(f"Adding conditional order {params} to new contract {owner}")
            self.orders[owner] = [
                ConditionalOrder(
                    params=params,
                    proof=proof,
                    orders={},
                    composableCow=composable_cow
                )
            ]

    def _flush_contracts(self, owner: str, root: str) -> None:
        """Flush contracts that have old roots."""
        conditional_orders = []
        for conditional_order in self.orders[owner]:
            if conditional_order.proof.merkleRoot is not None and conditional_order.proof.merkleRoot != root:
                conditional_orders.append(conditional_order)
        self.orders[owner] = conditional_orders

