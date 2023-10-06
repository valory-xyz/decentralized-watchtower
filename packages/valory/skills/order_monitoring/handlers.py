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

"""This package contains a scaffold of a handler."""

import json
from typing import Any, Dict, List, Optional, Tuple, cast
from uuid import uuid4

from aea.protocols.base import Message
from aea.skills.base import Handler
from web3 import Web3

from packages.valory.connections.ledger.connection import (
    PUBLIC_ID as LEDGER_CONNECTION_PUBLIC_ID,
)
from packages.valory.contracts.composable_cow.contract import (
    CallType,
    ComposableCowContract,
)
from packages.valory.protocols.contract_api import ContractApiMessage
from packages.valory.protocols.default.message import DefaultMessage
from packages.valory.skills.order_monitoring.models import Params
from packages.valory.skills.order_monitoring.order_utils import (
    ConditionalOrder,
    ConditionalOrderParamsStruct,
    Proof,
    balance_to_string,
    compute_order_uid,
    kind_to_string,
)


ORDERS = "orders"
# ready orders are orders that are ready to be filled
READY_ORDERS = "ready_orders"
DISCONNECTION_POINT = "disconnection_point"

LEDGER_API_ADDRESS = str(LEDGER_CONNECTION_PUBLIC_ID)

GPV2SETTLEMENT_CONTRACT_ADDRESS = "0x9008D19f58AAbD9eD0D60971565AA8510560ab41"


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
        self.context.shared_state[ORDERS] = {}
        self.context.shared_state[READY_ORDERS] = []
        self.context.shared_state[DISCONNECTION_POINT] = None

    @property
    def orders(self) -> Dict[str, Any]:
        """Get partial orders."""
        return self.context.shared_state[ORDERS]

    @property
    def ready_orders(self) -> List[Dict[str, Any]]:
        """Get orders."""
        return self.context.shared_state[READY_ORDERS]

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
        self._process_tx(tx_hash)

    def _process_tx(self, tx_hash: str) -> None:
        """Get the relevant events out of the transaction."""
        (contract_api_msg, _,) = self.context.contract_api_dialogues.create(
            performative=ContractApiMessage.Performative.GET_STATE,
            contract_address=self.contract_to_monitor,
            contract_id=str(ComposableCowContract.contract_id),
            callable="process_order_events",
            kwargs=ContractApiMessage.Kwargs(dict(tx_hash=tx_hash)),
            counterparty=LEDGER_API_ADDRESS,
            ledger_id=self.context.default_ledger_id,
        )
        self.context.outbox.put_message(message=contract_api_msg)

    def teardown(self) -> None:
        """Implement the handler teardown."""
        self.context.logger.info("WebSocketHandler teardown method called.")


class ContractHandler(Handler):
    """Contract API message handler."""

    SUPPORTED_PROTOCOL = ContractApiMessage.protocol_id

    def setup(self) -> None:
        """Setup the contract handler."""
        self.context.shared_state[ORDERS] = {}
        self.context.shared_state[READY_ORDERS] = []

    def teardown(self) -> None:
        """Teardown the handler."""
        self.context.logger.info("ContractHandler: teardown called.")

    @property
    def orders(self) -> Dict[str, List[ConditionalOrder]]:
        """Get partial orders."""
        return self.context.shared_state[ORDERS]

    @property
    def ready_orders(self) -> List[Dict[str, Any]]:
        """Get orders."""
        return self.context.shared_state[READY_ORDERS]

    @property
    def params(self) -> Params:
        """Get the parameters."""
        return cast(Params, self.context.params)

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
        call_type = body.get("type", None)
        data = body.get("data", {})
        if call_type == CallType.EVENT_PROCESSING.value:
            self._handle_event_processing(data)

        if call_type == CallType.GET_TRADEABLE_ORDER.value:
            self._handle_get_tradeable_order(data["tradeable_orders"], data["drop_orders"])

    def get_domain(  # pylint: disable=no-self-use
        self, order: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get domain."""
        domain = {
            "name": "Gnosis Protocol",
            "version": "v2",
            "chainId": order["chainId"],
            "verifyingContract": GPV2SETTLEMENT_CONTRACT_ADDRESS,
        }
        return domain

    def _handle_get_tradeable_order(
        self, tradeable_orders: List[Dict[str, Any]], drop_orders: List[Dict[str, Any]],
    ) -> None:
        """Handle get tradeable order."""
        for order in tradeable_orders:
            domain = self.get_domain(order)
            id = order.pop("id")
            order_uid = compute_order_uid(domain, order, order["from"])
            order["order_uid"] = order_uid
            # remove from orders
            owner = order["from"]
            owner_orders = self.orders.get(owner, [])
            # remove from orders
            self.orders[owner] = [o for o in owner_orders if o.id != id]

            # add to ready orders
            self.ready_orders.append(
                {
                    **order,
                    "sellAmount": str(order["sellAmount"]),
                    "buyAmount": str(order["buyAmount"]),
                    "feeAmount": str(order["feeAmount"]),
                    "sellTokenBalance": balance_to_string(order["sellTokenBalance"]),
                    "buyTokenBalance": balance_to_string(order["sellTokenBalance"]),
                    "kind": kind_to_string(order["kind"]),
                }
            )
        self.params.in_flight_req = False

    def _handle_event_processing(self, events: Dict[str, Any]) -> None:
        """Handle event processing."""
        conditional_orders = events.get("conditional_orders", [])
        merkle_root_set_events = events.get("merkle_root_set", [])
        for conditional_order in conditional_orders:
            self._add_contract(
                conditional_order["owner"],
                conditional_order["params"],
                conditional_order.get("proof", None),
                conditional_order.get("composableCow", None),
            )

        for merkle_root_set in merkle_root_set_events:
            self._flush_contracts(
                merkle_root_set["owner"],
                merkle_root_set["merkleRoot"],
            )
            for order in merkle_root_set["orders"]:
                self._add_contract(
                    merkle_root_set["owner"],
                    order["params"],
                    Proof(merkle_root_set["merkleRoot"], order["path"]),
                    order["address"],
                )

    def _add_contract(
        self,
        owner: str,
        params: Tuple[str, bytes, bytes],
        proof: Optional[Proof],
        composable_cow: str,
    ) -> None:
        """Add a conditional order to the registry."""
        if owner in self.orders:
            conditional_orders = self.orders[owner]
            self.context.logger.info(
                f"Adding conditional order {params} to already existing owner {owner}"
            )
            exists = False
            # Iterate over the conditionalOrder to make sure
            # that the params are not already in the registry
            for conditional_order in conditional_orders:
                # Check if the params are in the conditionalOrder
                if conditional_order.params == params:
                    exists = True
                    break

            # If the params are not in the conditionalOrder, add them
            # we essentially use the params as identifier for the conditional order
            if not exists:
                # this is a local id, it is not the same as the uid
                id = uuid4().hex
                conditional_order = ConditionalOrder(
                    id=id,
                    params=ConditionalOrderParamsStruct(
                        handler=params["handler"],
                        salt=params["salt"],
                        staticInput=params["staticInput"],
                    ),
                    proof=proof,
                    orders={},
                    composableCow=composable_cow,
                    offchainInput=b"",
                )
                conditional_orders.append(conditional_order)

        else:
            # this is the first order for this owner
            self.context.logger.info(
                f"Adding conditional order {params} to new contract {owner}"
            )
            # this is a local id, it is not the same as the uid
            id = uuid4().hex
            self.orders[owner] = [
                ConditionalOrder(
                    id=id,
                    params=ConditionalOrderParamsStruct(
                        handler=params["handler"],
                        salt=params["salt"],
                        staticInput=params["staticInput"],
                    ),
                    proof=proof,
                    orders={},
                    composableCow=composable_cow,
                    offchainInput=b"",
                )
            ]

    def _flush_contracts(self, owner: str, root: str) -> None:
        """Flush contracts that have old roots."""
        conditional_orders = []
        for conditional_order in self.orders[owner]:
            if (
                conditional_order.proof.merkleRoot is not None
                and conditional_order.proof.merkleRoot != root
            ):
                conditional_orders.append(conditional_order)
        self.orders[owner] = conditional_orders
