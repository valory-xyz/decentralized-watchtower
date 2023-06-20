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
# pylint: disable=undefined-loop-variable
"""This package contains the tests for rounds of CowOrders."""
import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Hashable, List, Mapping, Type, cast

from packages.valory.skills.abstract_round_abci.base import (
    AbstractRound,
    BaseTxPayload,
    get_name,
)
from packages.valory.skills.abstract_round_abci.test_tools.rounds import (
    BaseRoundTestClass,
)
from packages.valory.skills.cow_orders_abci.payloads import (
    PlaceOrdersPayload,
    SelectOrdersPayload,
)
from packages.valory.skills.cow_orders_abci.rounds import (
    Event,
    PlaceOrdersRound,
    SelectOrdersRound,
    SynchronizedData,
    VerifyExecutionRound,
)


@dataclass
class RoundTestCase:
    """RoundTestCase"""

    name: str
    initial_data: Dict[str, Hashable]
    payloads: Mapping[str, BaseTxPayload]
    final_data: Dict[str, Hashable]
    event: Event
    synchronized_data_attr_checks: List[Callable] = field(default_factory=list)
    kwargs: Dict[str, Any] = field(default_factory=dict)


MAX_PARTICIPANTS: int = 4
_DUMMY_ADDRESS = "0x000000"


class BaseCowOrdersRoundTest(
    BaseRoundTestClass
):  # pylint: disable=too-few-public-methods
    """Base test class for CowOrders rounds."""

    round_cls: Type[AbstractRound]
    synchronized_data: SynchronizedData
    _synchronized_data_class = SynchronizedData
    _event_class = Event


class TestPlaceOrdersRound(BaseCowOrdersRoundTest):
    """Tests for PlaceOrdersRound."""

    round_class = PlaceOrdersRound

    def test_run(self) -> None:
        """Tests the happy path for ObservationRound."""
        test_round = self.round_class(
            synchronized_data=self.synchronized_data,
        )
        participants = list(self.participants)
        keeper = participants[0]
        self.synchronized_data.update(
            synchronized_data_class=SynchronizedData,
            **{get_name(SynchronizedData.most_voted_keeper_address): keeper},
        )

        # before the first payload, the round should not end
        assert test_round.end_block() is None

        payload_data = "test"
        payload = PlaceOrdersPayload(sender=keeper, content=payload_data)

        # only one participant has voted, and
        # that should be enough for proceeding to the next round
        test_round.process_payload(payload)
        assert test_round.end_block() is not None


class TestSelectOrdersRound(BaseCowOrdersRoundTest):
    """Tests for SelectOrdersRound."""

    round_class = SelectOrdersRound

    def test_run(self) -> None:
        """Run tests."""

        test_round = self.round_class(
            synchronized_data=self.synchronized_data,
        )

        payload = dict(token="dummy_token", orders="dummy_orders")  # nosec
        serialized_payload = json.dumps(payload, sort_keys=True)
        first_payload, *payloads = [
            SelectOrdersPayload(sender=participant, content=serialized_payload)
            for participant in self.participants
        ]

        # only one participant has voted
        # no event should be returned
        test_round.process_payload(first_payload)
        assert test_round.collection[first_payload.sender] == first_payload
        assert test_round.end_block() is None

        # enough members have voted
        # but no majority is reached
        self._test_no_majority_event(test_round)

        # all members voted in the same way
        for payload in payloads:  # type: ignore
            test_round.process_payload(payload)  # type: ignore

        expected_next_state = cast(
            SynchronizedData,
            self.synchronized_data.update(
                participant_to_observations=self.round_class.serialize_collection(
                    test_round.collection
                ),
                most_voted_observation=cast(SelectOrdersPayload, payload).json,
            ),
        )

        res = test_round.end_block()
        assert res is not None
        state, event = res
        actual_next_state = cast(SynchronizedData, state)

        # check that the state is updated as expected
        assert actual_next_state.order == expected_next_state.order

        assert event == Event.DONE


class TestVerifyExecutionRound(BaseCowOrdersRoundTest):
    """Tests for VerifyExecutionRound."""

    round_class = VerifyExecutionRound

    def test_run(self) -> None:
        """Run tests."""

        test_round = self.round_class(
            synchronized_data=self.synchronized_data,
        )
        order = dict(token="dummy_token", orders="dummy_orders")  # nosec
        self.synchronized_data.update(
            synchronized_data_class=SynchronizedData,
            **{get_name(SynchronizedData.order): order},
        )
        serialized_payload = json.dumps(order, sort_keys=True)
        first_payload, *payloads = [
            SelectOrdersPayload(sender=participant, content=serialized_payload)
            for participant in self.participants
        ]

        # only one participant has voted
        # no event should be returned
        test_round.process_payload(first_payload)
        assert test_round.collection[first_payload.sender] == first_payload
        assert test_round.end_block() is None

        # enough members have voted
        # but no majority is reached
        self._test_no_majority_event(test_round)

        # all members voted in the same way
        for payload in payloads:  # type: ignore
            test_round.process_payload(payload)  # type: ignore

        expected_next_state = cast(
            SynchronizedData,
            self.synchronized_data.update(
                participant_to_observations=self.round_class.serialize_collection(
                    test_round.collection
                ),
                verified_order=cast(SelectOrdersPayload, payload).json,
            ),
        )

        res = test_round.end_block()
        assert res is not None
        state, event = res
        actual_next_state = cast(SynchronizedData, state)

        # check that the state is updated as expected
        assert actual_next_state.order == expected_next_state.order

        assert event == Event.DONE
