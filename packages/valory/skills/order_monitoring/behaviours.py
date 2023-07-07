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

"""This package contains a scaffold of a behaviour."""

import json
from typing import Any, Dict, List, Optional, cast

from aea.mail.base import Envelope
from aea.skills.behaviours import SimpleBehaviour

from packages.valory.protocols.default.message import DefaultMessage
from packages.valory.connections.websocket_client.connection import (
    CONNECTION_ID,
    WebSocketClient,
)
from packages.valory.contracts.composable_cow.contract import ComposableCowContract
from packages.valory.protocols.contract_api import ContractApiMessage
from packages.valory.skills.order_monitoring.handlers import (
    DISCONNECTION_POINT,
    LEDGER_API_ADDRESS,
    ORDERS,
)
from packages.valory.skills.order_monitoring.models import Params
from packages.valory.skills.order_monitoring.order_utils import ConditionalOrder


DEFAULT_ENCODING = "utf-8"
WEBSOCKET_CLIENT_CONNECTION_NAME = "websocket_client"


class MonitoringBehaviour(SimpleBehaviour):
    """This class scaffolds a behaviour."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialise the agent."""
        self._ws_client_connection: Optional[WebSocketClient] = None
        self._subscription_required: bool = True
        self._missed_parts: bool = False
        super().__init__(**kwargs)

    def setup(self) -> None:
        """Implement the setup."""
        use_polling = self.context.params.use_polling
        if use_polling:
            # if we are using polling, then we don't set up an contract subscription
            return
        for (
            connection
        ) in self.context.outbox._multiplexer.connections:  # pylint: disable=W0212
            if connection.component_id.name == WEBSOCKET_CLIENT_CONNECTION_NAME:
                self._ws_client_connection = cast(WebSocketClient, connection)

    def act(self) -> None:
        """Implement the act."""
        self._do_subscription()
        self._check_orders_are_tradeable()

    @property
    def params(self) -> Params:
        """Get the parameters."""
        return cast(Params, self.context.params)

    @property
    def orders(self) -> Dict[str, List[ConditionalOrder]]:
        """Get partial orders."""
        return self.context.shared_state[ORDERS]

    def _check_orders_are_tradeable(self) -> None:
        """Check if orders are tradeable."""
        if self.params.in_flight_req:
            # do nothing if there are no orders or if there is an in flight request
            return
        orders = [
            {
                "id": order.id,
                "owner": owner,
                "params": [
                    order.params.handler,
                    order.params.salt,
                    order.params.staticInput,
                ],
                "offchainInput": order.offchainInput,
                "proof": order.proof if order.proof is not None else [],
                "composableCow": order.composableCow,
            }
            for owner, owner_orders in self.orders.items()
            for order in owner_orders
        ]
        if len(orders) == 0:
            # do nothing if there are no orders
            return
        contract_api_msg, _ = self.context.contract_api_dialogues.create(
            performative=ContractApiMessage.Performative.GET_STATE,
            contract_address=self.params.composable_cow_address,
            contract_id=str(ComposableCowContract.contract_id),
            callable="get_tradeable_order",
            kwargs=ContractApiMessage.Kwargs(dict(orders=orders)),
            counterparty=LEDGER_API_ADDRESS,
            ledger_id=self.context.default_ledger_id,
        )
        self.context.outbox.put_message(message=contract_api_msg)
        self.params.in_flight_req = True

    def _do_subscription(self) -> None:
        """Handle subscription logic."""
        use_polling = self.context.params.use_polling
        if use_polling:
            # do nothing if we are polling
            return
        is_connected = cast(WebSocketClient, self._ws_client_connection).is_connected
        disconnection_point = self.context.shared_state.get(DISCONNECTION_POINT, None)

        if is_connected and self._subscription_required:
            # we only subscribe once, because the envelope
            # will remain in the multiplexer until handled
            topics = self.context.params.event_topics
            subscription_msg_template = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_subscribe",
                "params": ["logs", {"topics": topics}],
            }
            self.context.logger.info(f"Sending subscription for event topics: {topics}")
            self._create_call(
                bytes(json.dumps(subscription_msg_template), DEFAULT_ENCODING)
            )
        self._subscription_required = False
        if disconnection_point is not None:
            self._missed_parts = True

        if is_connected and self._missed_parts:
            # if we are connected and have a disconnection point,
            # then we need to fetch the parts that were missed
            topics = self.context.params.event_topics
            filter_msg_template = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_newFilter",
                "params": [{"fromBlock": disconnection_point, "topics": topics}],
            }
            self.context.logger.info(f"Creating filter for event topics: {topics}")
            self._create_call(bytes(json.dumps(filter_msg_template), DEFAULT_ENCODING))
            self.context.logger.info(
                "Getting parts that were missed while disconnected."
            )

        if (
            not is_connected
            and not self._subscription_required
            and disconnection_point is not None
        ):
            self.context.logger.warning(
                f"Disconnection detected on block {disconnection_point}."
            )

        if not is_connected:
            self._subscription_required = True

    def _create_call(self, content: bytes) -> None:
        """Create a call."""
        msg, _ = self.context.default_dialogues.create(
            counterparty=str(CONNECTION_ID),
            performative=DefaultMessage.Performative.BYTES,
            content=content,
        )
        # pylint: disable=W0212
        msg._sender = str(self.context.skill_id)
        envelope = Envelope(to=msg.to, sender=msg._sender, message=msg)
        self.context.outbox.put(envelope)
