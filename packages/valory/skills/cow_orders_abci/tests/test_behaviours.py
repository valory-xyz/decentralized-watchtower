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

"""This package contains round behaviours of CowOrdersAbciApp."""
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

import pytest

from packages.valory.skills.abstract_round_abci.base import AbciAppDB
from packages.valory.skills.abstract_round_abci.behaviours import BaseBehaviour
from packages.valory.skills.abstract_round_abci.test_tools.base import (
    FSMBehaviourBaseCase,
)
from packages.valory.skills.abstract_round_abci.test_tools.common import (
    BaseRandomnessBehaviourTest,
    BaseSelectKeeperBehaviourTest,
)
from packages.valory.skills.cow_orders_abci.behaviours import (
    CowOrdersBaseBehaviour,
    CowOrdersRoundBehaviour,
    DEFAULT_HTTP_HEADERS,
    ORDERS,
    PlaceOrdersBehaviour,
    RandomnessBehaviour,
    SelectKeeperBehaviour,
    SelectOrdersBehaviour,
    VerifyExecutionBehaviour,
)
from packages.valory.skills.cow_orders_abci.rounds import Event, SynchronizedData
from packages.valory.skills.cow_orders_abci.tests.test_rounds import get_keepers


_DEFAULT_COW_API = "https://api.cow.fi/mainnet/orders"
_DUMMY_ORDER_UID = "order_uid"
_DUMMY_ORDERS = [{"order_uid": _DUMMY_ORDER_UID, "keeper_id": "1", "amount": 1}]
_DEFAULT_HEADERS = ""
for key, val in DEFAULT_HTTP_HEADERS.items():
    _DEFAULT_HEADERS += f"{key}: {val}\r\n"


@dataclass
class BehaviourTestCase:
    """BehaviourTestCase"""

    name: str
    initial_data: Dict[str, Any]
    event: Event
    kwargs: Dict[str, Any] = field(default_factory=dict)
    orders: List[Dict[str, Any]] = field(default_factory=list)


class BaseCowOrdersTest(FSMBehaviourBaseCase):
    """Base test case."""

    path_to_skill = Path(__file__).parent.parent

    behaviour: CowOrdersRoundBehaviour
    behaviour_class: Type[CowOrdersBaseBehaviour]
    next_behaviour_class: Type[CowOrdersBaseBehaviour]
    synchronized_data: SynchronizedData
    done_event = Event.DONE

    @property
    def current_behaviour_id(self) -> str:
        """Current RoundBehaviour's behaviour id"""

        return self.behaviour.current_behaviour.behaviour_id

    def fast_forward(self, data: Optional[Dict[str, Any]] = None) -> None:
        """Fast-forward on initialization"""

        data = data if data is not None else {}
        self.fast_forward_to_behaviour(
            self.behaviour,
            self.behaviour_class.auto_behaviour_id(),
            SynchronizedData(AbciAppDB(setup_data=AbciAppDB.data_to_lists(data))),
        )
        assert self.current_behaviour_id == self.behaviour_class.auto_behaviour_id()

    def complete(self, event: Event, send_a2a_tx: bool = True) -> None:
        """Complete test"""

        self.behaviour.act_wrapper()
        if send_a2a_tx:
            self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round(done_event=event)
        assert (
            self.current_behaviour_id == self.next_behaviour_class.auto_behaviour_id()
        )


class TestPlaceOrdersBehaviour(BaseCowOrdersTest):
    """Tests PlaceOrdersBehaviour"""

    behaviour_class: Type[BaseBehaviour] = PlaceOrdersBehaviour
    next_behaviour_class: Type[BaseBehaviour] = VerifyExecutionBehaviour

    _MY_AGENT_ADDRESS = "test_agent_address"
    _OTHER_AGENT_ADDRESS = "other_agent_address"
    _KEEPERS = get_keepers(deque(("agent_1" + "-" * 35, "agent_3" + "-" * 35)))

    def _mock_place_order(self, **kwargs: Any) -> None:
        """Mock place order http request"""
        self.mock_http_request(
            request_kwargs=dict(
                method="POST",
                headers=_DEFAULT_HEADERS,
                version="",
                url=_DEFAULT_COW_API,
            ),
            response_kwargs=dict(
                version="",
                status_code=kwargs.get("status_code"),
                status_text="",
                headers="",
                body=kwargs.get("body").encode(),
            ),
        )

    @pytest.mark.parametrize(
        "test_case",
        [
            BehaviourTestCase(
                name="the keeper places the order",
                initial_data={
                    "order": _DUMMY_ORDERS[0],
                    "keepers": _KEEPERS,
                },
                event=Event.DONE,
                kwargs={"status_code": 201, "body": "dummy"},
                orders=_DUMMY_ORDERS,
            ),
            BehaviourTestCase(
                name="the keeper fails to place the order",
                initial_data={
                    "order": _DUMMY_ORDERS[0],
                    "keepers": _KEEPERS,
                },
                event=Event.DONE,
                kwargs={"status_code": 403, "body": "dummy"},
                orders=_DUMMY_ORDERS,
            ),
            BehaviourTestCase(
                name="non keepers wait",
                initial_data={
                    "order": _DUMMY_ORDERS[0],
                    "keepers": _KEEPERS,
                },
                event=Event.DONE,
                kwargs={},
                orders=_DUMMY_ORDERS,
            ),
        ],
    )
    def test_run(self, test_case: BehaviourTestCase) -> None:
        """Run tests."""
        self.fast_forward(test_case.initial_data)
        is_sender = (
            test_case.initial_data.get("most_voted_keeper_address")
            == self._MY_AGENT_ADDRESS
        )
        if is_sender:
            self.behaviour.act_wrapper()
            self._mock_place_order(**test_case.kwargs)
        self.complete(test_case.event, send_a2a_tx=is_sender)


class TestRandomnessInOperation(BaseRandomnessBehaviourTest):
    """Test randomness in operation."""

    path_to_skill = Path(__file__).parent.parent

    randomness_behaviour_class = RandomnessBehaviour
    next_behaviour_class = SelectKeeperBehaviour
    done_event = Event.DONE


class TestSelectKeeperBehaviour(BaseSelectKeeperBehaviourTest):
    """Test SelectKeeperBehaviour."""

    path_to_skill = Path(__file__).parent.parent

    select_keeper_behaviour_class = SelectKeeperBehaviour
    next_behaviour_class = PlaceOrdersBehaviour
    done_event = Event.DONE
    _synchronized_data = SynchronizedData


class TestSelectOrdersBehaviour(BaseCowOrdersTest):
    """Test SelectKeeperBehaviour."""

    behaviour_class: Type[BaseBehaviour] = SelectOrdersBehaviour
    next_behaviour_class: Type[BaseBehaviour] = RandomnessBehaviour

    @pytest.mark.parametrize(
        "test_case",
        [
            BehaviourTestCase(
                name="pending orders exist",
                initial_data={},
                event=Event.DONE,
                kwargs={},
                orders=_DUMMY_ORDERS,
            ),
            BehaviourTestCase(
                name="pending orders exist, and there is a processed order",
                initial_data={"verified_order": _DUMMY_ORDERS[0]},
                event=Event.DONE,
                kwargs={},
                orders=_DUMMY_ORDERS,
            ),
            BehaviourTestCase(
                name="no orders exists",
                initial_data={"verified_order": _DUMMY_ORDERS[0]},
                event=Event.DONE,
                kwargs={},
                orders=_DUMMY_ORDERS,
            ),
        ],
    )
    def test_run(self, test_case: BehaviourTestCase) -> None:
        """Run tests."""
        self.behaviour.context.shared_state[ORDERS] = test_case.orders
        self.fast_forward(test_case.initial_data)
        self.complete(test_case.event)


class TestVerifyExecutionBehaviour(BaseCowOrdersTest):
    """Tests VerifyExecutionBehaviour"""

    behaviour_class: Type[BaseBehaviour] = VerifyExecutionBehaviour
    next_behaviour_class: Type[BaseBehaviour] = SelectOrdersBehaviour

    def _mock_get_order(self, **kwargs: Any) -> None:
        """Mock place order http request"""
        self.mock_http_request(
            request_kwargs=dict(
                method="GET",
                headers=_DEFAULT_HEADERS,
                version="",
                url=f"{_DEFAULT_COW_API}/{kwargs.get('order_uid')}",
            ),
            response_kwargs=dict(
                version="",
                status_code=kwargs.get("status_code"),
                status_text="",
                headers="",
                body=kwargs.get("body").encode(),
            ),
        )

    @pytest.mark.parametrize(
        "test_case",
        [
            BehaviourTestCase(
                name="order is OK",
                initial_data={"order": _DUMMY_ORDERS[0], "order_uid": _DUMMY_ORDER_UID},
                event=Event.DONE,
                kwargs={
                    "status_code": 200,
                    "body": "dummy",
                    "order_uid": _DUMMY_ORDER_UID,
                },
                orders=_DUMMY_ORDERS,
            ),
            BehaviourTestCase(
                name="order is not submitted",
                initial_data={"order": _DUMMY_ORDERS[0], "order_uid": _DUMMY_ORDER_UID},
                event=Event.DONE,
                kwargs={
                    "status_code": 404,
                    "body": "dummy",
                    "order_uid": _DUMMY_ORDER_UID,
                },
                orders=_DUMMY_ORDERS,
            ),
            BehaviourTestCase(
                name="order is badly submitted",
                initial_data={
                    "order": _DUMMY_ORDERS[0],
                    "order_uid": _DUMMY_ORDER_UID + "bad",
                },
                event=Event.DONE,
                kwargs={
                    "status_code": 200,
                    "body": "dummy",
                    "order_uid": _DUMMY_ORDER_UID,
                },
                orders=_DUMMY_ORDERS,
            ),
        ],
    )
    def test_run(self, test_case: BehaviourTestCase) -> None:
        """Run tests."""
        self.behaviour.context.shared_state[ORDERS] = test_case.orders
        self.fast_forward(test_case.initial_data)
        self.behaviour.act_wrapper()
        if test_case.initial_data.get("order_uid") == _DUMMY_ORDER_UID:
            self._mock_get_order(**test_case.kwargs)
        self.complete(test_case.event)
