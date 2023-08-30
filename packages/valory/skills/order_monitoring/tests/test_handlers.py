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

"""Tests for the handlers of the order_monitoring skill."""

from typing import Any, Optional
from unittest.mock import MagicMock

from packages.valory.protocols.contract_api import ContractApiMessage
from packages.valory.skills.order_monitoring.handlers import (
    ContractHandler,
    GPV2SETTLEMENT_CONTRACT_ADDRESS,
    ORDERS,
    WebSocketHandler,
)
from packages.valory.skills.order_monitoring.order_utils import (
    ConditionalOrder,
    ConditionalOrderParamsStruct,
    Proof,
)


class TestWebSocketHandler:
    """Test the WebSocketHandler class."""

    def setup(self) -> None:
        """Set up the test case."""
        self.websocket_provider: Optional[Any] = None
        self.contract_to_monitor: Optional[Any] = None
        context = MagicMock()
        self.handler = WebSocketHandler(
            name="handler",
            skill_context=context,
            websocket_provider=self.websocket_provider,
            contract_to_monitor=self.contract_to_monitor,
        )
        self.handler.context.shared_state = {}
        self.handler.context.default_ledger_id = "default_ledger"
        self.handler.context.contract_api_dialogues = MagicMock()

    def test_setup(self) -> None:
        """Test setup method of WebSocketHandler."""
        self.handler.setup()
        assert "orders" in self.handler.context.shared_state
        assert "ready_orders" in self.handler.context.shared_state
        assert "disconnection_point" in self.handler.context.shared_state

    def test_orders(self) -> None:
        """Test orders property of WebSocketHandler."""
        self.handler.context.shared_state["orders"] = {"owner1": []}
        assert self.handler.orders == {"owner1": []}

    def test_ready_orders(self) -> None:
        """Test ready_orders property of WebSocketHandler."""
        self.handler.context.shared_state["ready_orders"] = []
        assert self.handler.ready_orders == []

    def test_handle_response_message(self) -> None:
        """Test handle_response_message method of WebSocketHandler."""
        message = MagicMock(content='{"id": 1, "result": "success", "jsonrpc": "2.0"}')
        self.handler.handle(message)
        assert self.handler.context.logger.info.call_count == 2

    def test_handle_data_message(self) -> None:
        """Test handle_data_message method of WebSocketHandler."""
        message = MagicMock(
            content='{"params": {"result": {"transactionHash": "hash"}}, "other_field": "value"}'
        )
        self.handler._process_tx = MagicMock()
        self.handler.handle(message)
        self.handler._process_tx.assert_called_once_with("hash")

    def test_process_tx(self) -> None:
        """Test _process_tx method of WebSocketHandler."""
        tx_hash = "hash"
        contract_api_msg = MagicMock()
        contract_api_dialogue = MagicMock()
        self.handler.context.contract_api_dialogues.create.return_value = (
            contract_api_msg,
            contract_api_dialogue,
        )
        self.handler._process_tx(tx_hash)
        self.handler.context.contract_api_dialogues.create.assert_called_once()

    def test_teardown(self) -> None:
        """Test teardown method of WebSocketHandler."""
        self.handler.teardown()
        assert self.handler.context.logger.info.call_count == 1


class TestContractHandler:
    """Test ContractHandler class of order_monitoring skill."""

    def setup(self) -> None:
        """Setup the test."""
        context = MagicMock()
        self.handler = ContractHandler(
            name="handler",
            skill_context=context,
        )
        self.handler.context.shared_state = {}
        self.handler.context.logger = MagicMock()
        self.handler.setup()

    def test_orders(self) -> None:
        """Test orders property of ContractHandler."""
        self.handler.context.shared_state["orders"] = {"owner1": []}
        assert self.handler.orders == {"owner1": []}

    def test_ready_orders(self) -> None:
        """Test ready_orders property of ContractHandler."""
        self.handler.context.shared_state["ready_orders"] = []
        assert self.handler.ready_orders == []

    def test_handle_invalid_performative(self) -> None:
        """Test handle method of ContractHandler for invalid performative."""
        contract_api_msg = MagicMock(performative="invalid")
        self.handler.handle(contract_api_msg)
        assert self.handler.context.logger.warning.call_count == 1

    def test_handle_get_tradeable_order(self) -> None:
        """Test handle method of ContractHandler for get_tradeable_order performative."""
        order = {"chainId": "chain_id", "from": "from_address"}
        tradeable_orders = [order]
        contract_api_msg = MagicMock(
            performative=ContractApiMessage.Performative.STATE,
            state=MagicMock(body={"type": "tradable_order", "data": tradeable_orders}),
        )
        self.handler._handle_get_tradeable_order = MagicMock()
        self.handler.handle(contract_api_msg)
        self.handler._handle_get_tradeable_order.assert_called()

    def test_handle_event_processing(self) -> None:
        """Test handle method of ContractHandler for event_processing performative."""
        conditional_order = {
            "owner": "owner",
            "params": ("param1", b"param2", b"param3"),
        }
        merkle_root_set = {"owner": "owner", "merkleRoot": "root", "orders": []}
        events = {
            "conditional_orders": [conditional_order],
            "merkle_root_set": [merkle_root_set],
        }
        contract_api_msg = MagicMock(
            performative=ContractApiMessage.Performative.STATE,
            state=MagicMock(body={"type": "event_processing", "data": events}),
        )
        self.handler._add_contract = MagicMock()
        self.handler._flush_contracts = MagicMock()
        self.handler.handle(contract_api_msg)
        self.handler._add_contract.assert_called_once_with(
            "owner", ("param1", b"param2", b"param3"), None, None
        )
        self.handler._flush_contracts.assert_called_once_with("owner", "root")

    def test_get_domain(self) -> None:
        """Test get_domain method of ContractHandler."""
        order = {"chainId": "chain_id"}
        expected_domain = {
            "name": "Gnosis Protocol",
            "version": "v2",
            "chainId": "chain_id",
            "verifyingContract": GPV2SETTLEMENT_CONTRACT_ADDRESS,
        }
        assert self.handler.get_domain(order) == expected_domain

    def test_add_contract_existing_owner(self) -> None:
        """
        Test _add_contract method of ContractHandler for existing owner.
        """
        params = {"handler": "param1", "salt": b"param2", "staticInput": b"param3"}
        self.handler.context.shared_state[ORDERS]["owner"] = []
        self.handler._add_contract("owner", params, None, None)
        assert len(self.handler.orders["owner"]) == 1
        assert self.handler.context.logger.info.call_count == 1

    def test_add_contract_new_owner(self) -> None:
        """
        Test _add_contract method of ContractHandler for new owner.
        """
        params = {"handler": "param1", "salt": b"param2", "staticInput": b"param3"}
        self.handler._add_contract("owner", params, None, None)
        assert len(self.handler.orders) == 1
        assert len(self.handler.orders["owner"]) == 1
        assert self.handler.context.logger.info.call_count == 1

    def test_flush_contracts(self) -> None:
        """
        Test _flush_contracts method of ContractHandler.
        """
        owner = "owner"
        root = "root"
        conditional_order = ConditionalOrder(
            id="id",
            params=ConditionalOrderParamsStruct("param1", b"param2", b"param3"),
            proof=Proof("root", "path"),
            orders={},
            composableCow=None,
            offchainInput=b"",
        )
        self.handler.context.shared_state[ORDERS] = {owner: [conditional_order]}
        self.handler._flush_contracts(owner, root)
        assert len(self.handler.orders[owner]) == 0
