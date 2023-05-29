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

"""This package contains the rounds of CowOrdersAbciApp."""
import textwrap
from collections import deque
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, cast, Deque

from packages.valory.skills.abstract_round_abci.base import (
    AbciApp,
    AbciAppTransitionFunction,
    AbstractRound,
    AppState,
    BaseSynchronizedData,
    DegenerateRound,
    EventToTimeout, CollectSameUntilThresholdRound, get_name, DeserializedCollection, CollectionRound,
)

from packages.valory.skills.cow_orders_abci.payloads import (
    PlaceOrdersPayload,
    RandomnessPayload,
    SelectKeeperPayload,
    SelectOrdersPayload,
    VerifyExecutionPayload,
)


MAX_INT_256 = 2**256 - 1
ADDRESS_LENGTH = 42
RETRIES_LENGTH = 64


class Event(Enum):
    """CowOrdersAbciApp Events"""

    NO_MAJORITY = "no_majority"
    ROUND_TIMEOUT = "round_timeout"
    NO_ACTION = "no_action"
    BAD_SUBMISSION = "bad_submission"
    DONE = "done"


class SynchronizedData(BaseSynchronizedData):
    """
    Class to represent the synchronized data.

    This data is replicated by the tendermint application.
    """

    @property
    def keeper_randomness(self) -> float:
        """Get the keeper's random number [0-1]."""
        return (
            int(self.most_voted_randomness, base=16) / MAX_INT_256
        )  # DRAND uses sha256 values

    @property
    def most_voted_randomness(self) -> str:
        """Get the most_voted_randomness."""
        return cast(str, self.db.get_strict("most_voted_randomness"))

    @property
    def most_voted_randomness_round(self) -> int:  # pragma: no cover
        """Get the first in priority keeper to try to re-submit a transaction."""
        round_ = self.db.get_strict("most_voted_randomness_round")
        return cast(int, round_)

    @property
    def most_voted_keeper_address(self) -> str:
        """Get the most_voted_keeper_address."""
        return cast(str, self.db.get_strict("most_voted_keeper_address"))

    @property
    def is_keeper_set(self) -> bool:
        """Check whether keeper is set."""
        return self.db.get("most_voted_keeper_address", None) is not None

    @property
    def blacklisted_keepers(self) -> Set[str]:
        """Get the current cycle's blacklisted keepers who cannot submit a transaction."""
        raw = cast(str, self.db.get("blacklisted_keepers", ""))
        return set(textwrap.wrap(raw, ADDRESS_LENGTH))

    @property
    def participant_to_selection(self) -> DeserializedCollection:
        """Check whether keeper is set."""
        serialized = self.db.get_strict("participant_to_selection")
        deserialized = CollectionRound.deserialize_collection(serialized)
        return cast(DeserializedCollection, deserialized)

    @property
    def keepers(self) -> Deque[str]:
        """Get the current cycle's keepers who have tried to submit a transaction."""
        if self.is_keeper_set:
            keepers_unparsed = cast(str, self.db.get_strict("keepers"))
            keepers_parsed = textwrap.wrap(
                keepers_unparsed[RETRIES_LENGTH:], ADDRESS_LENGTH
            )
            return deque(keepers_parsed)
        return deque()

class PlaceOrdersRound(AbstractRound):
    """PlaceOrdersRound"""

    payload_class = PlaceOrdersPayload
    payload_attribute = ""  # TODO: update
    synchronized_data_class = SynchronizedData

    # TODO: replace AbstractRound with one of CollectDifferentUntilAllRound,
    # CollectSameUntilAllRound, CollectSameUntilThresholdRound,
    # CollectDifferentUntilThresholdRound, OnlyKeeperSendsRound, VotingRound,
    # from packages/valory/skills/abstract_round_abci/base.py
    # or implement the methods

    def end_block(self) -> Optional[Tuple[BaseSynchronizedData, Enum]]:
        """Process the end of the block."""
        raise NotImplementedError

    def check_payload(self, payload: PlaceOrdersPayload) -> None:
        """Check payload."""
        raise NotImplementedError

    def process_payload(self, payload: PlaceOrdersPayload) -> None:
        """Process payload."""
        raise NotImplementedError


class RandomnessRound(CollectSameUntilThresholdRound):
    """A round for generating randomness"""

    payload_class = RandomnessPayload
    synchronized_data_class = SynchronizedData
    done_event = Event.DONE
    no_majority_event = Event.NO_MAJORITY
    collection_key = get_name(SynchronizedData.participant_to_randomness)
    selection_key = (
        get_name(SynchronizedData.most_voted_randomness_round),
        get_name(SynchronizedData.most_voted_randomness),
    )

class SelectKeeperRound(CollectSameUntilThresholdRound):
    """A round in which a keeper is selected for transaction submission"""

    payload_class = SelectKeeperPayload
    synchronized_data_class = SynchronizedData
    done_event = Event.DONE
    no_majority_event = Event.NO_MAJORITY
    collection_key = get_name(SynchronizedData.participant_to_selection)
    selection_key = get_name(SynchronizedData.keepers)

class SelectOrdersRound(AbstractRound):
    """SelectOrdersRound"""

    payload_class = SelectOrdersPayload
    payload_attribute = ""  # TODO: update
    synchronized_data_class = SynchronizedData

    # TODO: replace AbstractRound with one of CollectDifferentUntilAllRound,
    # CollectSameUntilAllRound, CollectSameUntilThresholdRound,
    # CollectDifferentUntilThresholdRound, OnlyKeeperSendsRound, VotingRound,
    # from packages/valory/skills/abstract_round_abci/base.py
    # or implement the methods

    def end_block(self) -> Optional[Tuple[BaseSynchronizedData, Enum]]:
        """Process the end of the block."""
        raise NotImplementedError

    def check_payload(self, payload: SelectOrdersPayload) -> None:
        """Check payload."""
        raise NotImplementedError

    def process_payload(self, payload: SelectOrdersPayload) -> None:
        """Process payload."""
        raise NotImplementedError


class VerifyExecutionRound(AbstractRound):
    """VerifyExecutionRound"""

    payload_class = VerifyExecutionPayload
    payload_attribute = ""  # TODO: update
    synchronized_data_class = SynchronizedData

    # TODO: replace AbstractRound with one of CollectDifferentUntilAllRound,
    # CollectSameUntilAllRound, CollectSameUntilThresholdRound,
    # CollectDifferentUntilThresholdRound, OnlyKeeperSendsRound, VotingRound,
    # from packages/valory/skills/abstract_round_abci/base.py
    # or implement the methods

    def end_block(self) -> Optional[Tuple[BaseSynchronizedData, Enum]]:
        """Process the end of the block."""
        raise NotImplementedError

    def check_payload(self, payload: VerifyExecutionPayload) -> None:
        """Check payload."""
        raise NotImplementedError

    def process_payload(self, payload: VerifyExecutionPayload) -> None:
        """Process payload."""
        raise NotImplementedError


class FinishedWithOrdersRound(DegenerateRound):
    """FinishedWithOrdersRound"""


class CowOrdersAbciApp(AbciApp[Event]):
    """CowOrdersAbciApp"""

    initial_round_cls: AppState = SelectOrdersRound
    initial_states: Set[AppState] = {SelectOrdersRound}
    transition_function: AbciAppTransitionFunction = {
        SelectOrdersRound: {
            Event.DONE: RandomnessRound,
            Event.NO_MAJORITY: SelectOrdersRound,
            Event.ROUND_TIMEOUT: SelectOrdersRound,
            Event.NO_ACTION: FinishedWithOrdersRound
        },
        RandomnessRound: {
            Event.DONE: SelectKeeperRound,
            Event.NO_MAJORITY: RandomnessRound,
            Event.ROUND_TIMEOUT: RandomnessRound
        },
        SelectKeeperRound: {
            Event.DONE: PlaceOrdersRound,
            Event.NO_MAJORITY: RandomnessRound,
            Event.ROUND_TIMEOUT: SelectKeeperRound
        },
        PlaceOrdersRound: {
            Event.DONE: VerifyExecutionRound,
            Event.NO_MAJORITY: PlaceOrdersRound,
            Event.ROUND_TIMEOUT: PlaceOrdersRound
        },
        VerifyExecutionRound: {
            Event.DONE: FinishedWithOrdersRound,
            Event.BAD_SUBMISSION: RandomnessRound,
            Event.NO_MAJORITY: PlaceOrdersRound,
            Event.ROUND_TIMEOUT: PlaceOrdersRound
        },
        FinishedWithOrdersRound: {}
    }
    final_states: Set[AppState] = {FinishedWithOrdersRound}
    event_to_timeout: EventToTimeout = {}
    cross_period_persisted_keys: Set[str] = []
    db_pre_conditions: Dict[AppState, Set[str]] = {
        SelectOrdersRound: [],
    }
    db_post_conditions: Dict[AppState, Set[str]] = {
        FinishedWithOrdersRound: [],
    }
