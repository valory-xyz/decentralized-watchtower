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
# pylint: skip-file

"""This module contains tests for order_monitoring behaviour."""

from unittest.mock import MagicMock

from packages.valory.protocols.default.message import DefaultMessage
from packages.valory.skills.order_monitoring import PUBLIC_ID
from packages.valory.skills.order_monitoring.behaviours import MonitoringBehaviour
from packages.valory.skills.order_monitoring.handlers import (
    DISCONNECTION_POINT,
    LEDGER_API_ADDRESS,
    ORDERS,
)
from packages.valory.skills.order_monitoring.order_utils import (
    ConditionalOrder,
    ConditionalOrderParamsStruct,
)


class TestMonitoringBehaviour:
    """Test the MonitoringBehaviour class."""

    def setup(self) -> None:
        """Initialise the behaviour and the required objects."""
        self.behaviour = MonitoringBehaviour(
            name="behaviour",
            skill_context=MagicMock(),
        )
        self.behaviour.context.params = MagicMock()
        self.behaviour.context.logger = MagicMock()
        self.behaviour.context.outbox = MagicMock()
        self.behaviour.context.shared_state = {}
        self.behaviour.context.contract_api_dialogues = MagicMock()

    def test_setup_with_polling(self) -> None:
        """Test the setup method of the MonitoringBehaviour class where use_polling is True."""
        self.behaviour.context.params.use_polling = True
        self.behaviour.setup()
        assert self.behaviour._ws_client_connection is None

    def test_act(self) -> None:
        """Test the act method of the MonitoringBehaviour class."""
        self.behaviour._do_subscription = MagicMock()
        self.behaviour._check_orders_are_tradeable = MagicMock()
        self.behaviour.act()
        self.behaviour._do_subscription.assert_called_once()
        self.behaviour._check_orders_are_tradeable.assert_called_once()

    def test_orders(self) -> None:
        """Test orders property of MonitoringBehaviour."""
        self.behaviour.context.shared_state[ORDERS] = {"owner1": []}
        assert self.behaviour.context.shared_state[ORDERS] == {"owner1": []}

    def test_check_orders_are_tradeable_with_in_flight_req(self) -> None:
        """Test the _check_orders_are_tradeable method of the MonitoringBehaviour class where there is an in flight request."""
        self.behaviour.params.in_flight_req = True
        self.behaviour.context.shared_state[ORDERS] = {
            "owner1": [
                ConditionalOrder(
                    id="1",
                    params=None,
                    proof=None,
                    orders={},
                    composableCow=None,
                    offchainInput=b"",
                )
            ]
        }
        self.behaviour._check_orders_are_tradeable()
        assert self.behaviour.context.contract_api_dialogues.create.call_count == 0
        assert self.behaviour.context.outbox.put_message.call_count == 0

    def test_check_orders_are_tradeable_with_no_orders(self) -> None:
        """Test the _check_orders_are_tradeable method of the MonitoringBehaviour class where there are no orders."""
        self.behaviour.params.in_flight_req = False
        self.behaviour.context.shared_state[ORDERS] = {}
        self.behaviour._check_orders_are_tradeable()
        assert self.behaviour.context.contract_api_dialogues.create.call_count == 0
        assert self.behaviour.context.outbox.put_message.call_count == 0

    def test_check_orders_are_tradeable_with_valid_orders(self) -> None:
        """Test the _check_orders_are_tradeable method of the MonitoringBehaviour class where the orders are valid."""
        self.behaviour.params.in_flight_req = False
        self.behaviour.context.contract_api_dialogues.create = MagicMock(
            return_value=(MagicMock(), MagicMock())
        )
        params = ConditionalOrderParamsStruct("handler", b"salt", b"static_input")
        self.behaviour.context.shared_state[ORDERS] = {
            "owner1": [
                ConditionalOrder(
                    id="1",
                    params=params,
                    proof=None,
                    orders={},
                    composableCow=None,
                    offchainInput=b"offchain_input",
                )
            ]
        }
        self.behaviour._check_orders_are_tradeable()
        assert self.behaviour.context.outbox.put_message.call_count == 1

    def test_do_subscription_with_polling(self) -> None:
        """Test the _do_subscription method of the MonitoringBehaviour class where the polling is used."""
        self.behaviour.context.params.use_polling = True
        self.behaviour._ws_client_connection = MagicMock()
        self.behaviour._subscription_required = True
        self.behaviour.context.shared_state[DISCONNECTION_POINT] = "disconnection_point"
        self.behaviour._do_subscription()
        assert self.behaviour.context.logger.warning.call_count == 0
        assert self.behaviour.context.outbox.put.call_count == 0

    def test_do_subscription_when_not_connected_and_subscription_required(self) -> None:
        """Test the _do_subscription method of the MonitoringBehaviour class where the connection is not established and the subscription is required."""
        self.behaviour.context.params.use_polling = False
        self.behaviour._ws_client_connection = MagicMock(is_connected=False)
        self.behaviour._subscription_required = True
        self.behaviour.context.shared_state[DISCONNECTION_POINT] = None
        self.behaviour._do_subscription()
        assert self.behaviour.context.logger.warning.call_count == 0
        assert self.behaviour.context.outbox.put.call_count == 0

    def test_do_subscription_when_connected_and_subscription_required(self) -> None:
        """Test the _do_subscription method of the MonitoringBehaviour class where the connection is established and the subscription is required."""
        self.behaviour.context.params.use_polling = False
        self.behaviour.context.params.event_topics = "0x0"
        self.behaviour.context.skill_id = str(PUBLIC_ID)
        self.behaviour._ws_client_connection = MagicMock(is_connected=True)
        message = DefaultMessage(performative=DefaultMessage.Performative.BYTES)
        message._to = LEDGER_API_ADDRESS
        self.behaviour.context.default_dialogues.create = MagicMock(
            return_value=(
                message,
                MagicMock(),
            )
        )
        self.behaviour._subscription_required = True
        self.behaviour.context.shared_state[DISCONNECTION_POINT] = None
        self.behaviour._do_subscription()
        assert self.behaviour.context.logger.warning.call_count == 0
        assert self.behaviour.context.outbox.put.call_count == 1

    def test_do_subscription_when_connected_and_subscription_not_required(self) -> None:
        """Test the _do_subscription method of the behaviour where the agent is connected and subscription is not required."""
        self.behaviour.context.params.use_polling = False
        self.behaviour._ws_client_connection = MagicMock(is_connected=True)
        self.behaviour._subscription_required = False
        self.behaviour.context.shared_state[DISCONNECTION_POINT] = None
        self.behaviour._do_subscription()
        assert self.behaviour.context.logger.warning.call_count == 0
        assert self.behaviour.context.outbox.put.call_count == 0

    def test_do_subscription_when_disconnected_and_subscription_required(self) -> None:
        """Test the _do_subscription method of the behaviour where the agent is disconnected and subscription is required."""
        self.behaviour.context.params.use_polling = False
        self.behaviour._ws_client_connection = MagicMock(is_connected=False)
        self.behaviour._subscription_required = True
        self.behaviour.context.shared_state[DISCONNECTION_POINT] = "disconnection_point"
        self.behaviour._do_subscription()
        assert self.behaviour.context.logger.warning.call_count == 1
        assert self.behaviour.context.outbox.put.call_count == 0

    def test_do_subscription_when_disconnected_and_no_missed_parts(self) -> None:
        """Test the _do_subscription method of the behaviour where the agent is disconnected and there are no missed parts."""
        self.behaviour.context.params.use_polling = False
        self.behaviour._ws_client_connection = MagicMock(is_connected=False)
        self.behaviour._subscription_required = False
        self.behaviour.context.shared_state[DISCONNECTION_POINT] = "disconnection_point"
        self.behaviour._missed_parts = False
        self.behaviour._do_subscription()
        assert self.behaviour.context.logger.warning.call_count == 1
        assert self.behaviour.context.outbox.put.call_count == 0
