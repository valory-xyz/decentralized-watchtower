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

from abc import ABC
from collections import deque
from typing import Generator, Set, Type, cast, Deque

from packages.valory.skills.abstract_round_abci.base import AbstractRound
from packages.valory.skills.abstract_round_abci.behaviours import (
    AbstractRoundBehaviour,
    BaseBehaviour,
)

from packages.valory.skills.cow_orders_abci.models import Params
from packages.valory.skills.cow_orders_abci.rounds import (
    SynchronizedData,
    CowOrdersAbciApp,
    PlaceOrdersRound,
    RandomnessRound,
    SelectKeeperRound,
    SelectOrdersRound,
    VerifyExecutionRound,
)
from packages.valory.skills.cow_orders_abci.rounds import (
    PlaceOrdersPayload,
    RandomnessPayload,
    SelectKeeperPayload,
    SelectOrdersPayload,
    VerifyExecutionPayload,
)
from packages.valory.skills.abstract_round_abci.common import (
    RandomnessBehaviour as BaseRandomnessBehaviour,
    SelectKeeperBehaviour as BaseSelectKeeperBehaviour,
)


class CowOrdersBaseBehaviour(BaseBehaviour, ABC):
    """Base behaviour for the cow_orders_abci skill."""

    @property
    def synchronized_data(self) -> SynchronizedData:
        """Return the synchronized data."""
        return cast(SynchronizedData, super().synchronized_data)

    @property
    def params(self) -> Params:
        """Return the params."""
        return cast(Params, super().params)

    @staticmethod
    def serialized_keepers(keepers: Deque[str], keeper_retries: int) -> str:
        """Get the keepers serialized."""
        if len(keepers) == 0:
            return ""
        keepers_ = "".join(keepers)
        keeper_retries_ = keeper_retries.to_bytes(32, "big").hex()
        concatenated = keeper_retries_ + keepers_

        return concatenated


class PlaceOrdersBehaviour(CowOrdersBaseBehaviour):
    """PlaceOrdersBehaviour"""

    matching_round: Type[AbstractRound] = PlaceOrdersRound

    # TODO: implement logic required to set payload content for synchronization
    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            sender = self.context.agent_address
            payload = PlaceOrdersPayload(sender=sender, content=...)

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()


class RandomnessBehaviour(BaseRandomnessBehaviour, CowOrdersBaseBehaviour):
    """RandomnessBehaviour"""

    matching_round: Type[AbstractRound] = RandomnessRound
    payload_class = RandomnessPayload


class SelectKeeperBehaviour(BaseSelectKeeperBehaviour, CowOrdersBaseBehaviour):
    """SelectKeeperBehaviour"""

    matching_round: Type[AbstractRound] = SelectKeeperRound
    payload_class = SelectKeeperPayload

    def async_act(self) -> Generator:
        """Do the action."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            keepers = deque((self._select_keeper(),))
            payload = self.payload_class(
                self.context.agent_address, self.serialized_keepers(keepers, 1)
            )

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()


class SelectOrdersBehaviour(CowOrdersBaseBehaviour):
    """SelectOrdersBehaviour"""

    matching_round: Type[AbstractRound] = SelectOrdersRound

    # TODO: implement logic required to set payload content for synchronization
    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            sender = self.context.agent_address
            payload = SelectOrdersPayload(sender=sender, content=...)

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()


class VerifyExecutionBehaviour(CowOrdersBaseBehaviour):
    """VerifyExecutionBehaviour"""

    matching_round: Type[AbstractRound] = VerifyExecutionRound

    # TODO: implement logic required to set payload content for synchronization
    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            sender = self.context.agent_address
            payload = VerifyExecutionPayload(sender=sender, content=...)

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()


class CowOrdersRoundBehaviour(AbstractRoundBehaviour):
    """CowOrdersRoundBehaviour"""

    initial_behaviour_cls = SelectOrdersBehaviour
    abci_app_cls = CowOrdersAbciApp  # type: ignore
    behaviours: Set[Type[BaseBehaviour]] = [
        PlaceOrdersBehaviour,
        RandomnessBehaviour,
        SelectKeeperBehaviour,
        SelectOrdersBehaviour,
        VerifyExecutionBehaviour
    ]
