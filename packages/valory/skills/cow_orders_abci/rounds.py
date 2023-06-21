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
import json
import textwrap
from collections import deque
from enum import Enum
from typing import Any, Deque, Dict, Optional, Set, Tuple, cast

from packages.valory.skills.abstract_round_abci.base import (
    AbciApp,
    AbciAppTransitionFunction,
    AppState,
    BaseSynchronizedData,
    CollectSameUntilThresholdRound,
    CollectionRound,
    DegenerateRound,
    DeserializedCollection,
    EventToTimeout,
    OnlyKeeperSendsRound,
    get_name,
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
        return self.keepers[0]

    @property
    def is_keeper_set(self) -> bool:
        """Check whether keeper is set."""
        return bool(self.db.get("keepers", False))

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

    @property
    def order_uid(self) -> str:
        """Get the order."""
        return cast(str, self.db.get_strict("order_uid"))

    @property
    def order(self) -> Dict[str, Any]:
        """Get the order."""
        return cast(Dict[str, Any], self.db.get_strict("order"))

    @property
    def verified_order(self) -> Optional[Dict[str, Any]]:
        """Get the order."""
        return cast(Optional[Dict[str, Any]], self.db.get("verified_order", None))


class PlaceOrdersRound(OnlyKeeperSendsRound):
    """PlaceOrdersRound"""

    keeper_payload: Optional[PlaceOrdersPayload] = None
    payload_class = PlaceOrdersPayload
    payload_attribute = "content"
    synchronized_data_class = SynchronizedData

    ERROR_PAYLOAD = "error"

    def end_block(self) -> Optional[Tuple[BaseSynchronizedData, Enum]]:
        """End the block."""
        if self.keeper_payload is None:
            return None

        # even if the content is ERROR_PAYLOAD, we still want to update the state
        order_uid = self.keeper_payload.content
        state = self.synchronized_data.update(
            synchronized_data_class=self.synchronized_data_class,
            **{
                get_name(SynchronizedData.order_uid): order_uid,
            }
        )
        return state, Event.DONE


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


class SelectOrdersRound(CollectSameUntilThresholdRound):
    """SelectOrdersRound"""

    payload_class = SelectOrdersPayload
    payload_attribute = "content"
    synchronized_data_class = SynchronizedData

    NO_ORDERS_PAYLOAD = "no_orders_payload"

    def end_block(self) -> Optional[Tuple[BaseSynchronizedData, Enum]]:
        """Process the end of the block."""
        if self.threshold_reached:
            if self.most_voted_payload == self.NO_ORDERS_PAYLOAD:
                return self.synchronized_data, Event.NO_ACTION
            order = json.loads(self.most_voted_payload)
            state = self.synchronized_data.update(
                synchronized_data_class=self.synchronized_data_class,
                **{
                    get_name(SynchronizedData.order): order,
                }
            )
            return state, Event.DONE

        if not self.is_majority_possible(
            self.collection, self.synchronized_data.nb_participants
        ):
            return self.synchronized_data, Event.NO_MAJORITY

        return None


class VerifyExecutionRound(CollectSameUntilThresholdRound):
    """VerifyExecutionRound"""

    payload_class = VerifyExecutionPayload
    payload_attribute = "content"
    synchronized_data_class = SynchronizedData

    VERIFICATION_FAILED = "verification_failed"
    VERIFICATION_OK = "verification_ok"

    def end_block(self) -> Optional[Tuple[BaseSynchronizedData, Enum]]:
        """Process the end of the block."""
        if self.threshold_reached:
            if self.most_voted_payload == self.VERIFICATION_FAILED:
                return self.synchronized_data, Event.BAD_SUBMISSION

            processed_order = cast(SynchronizedData, self.synchronized_data).order
            state = self.synchronized_data.update(
                synchronized_data_class=self.synchronized_data_class,
                **{
                    get_name(SynchronizedData.verified_order): processed_order,
                }
            )
            return state, Event.DONE
        if not self.is_majority_possible(
            self.collection, self.synchronized_data.nb_participants
        ):
            return self.synchronized_data, Event.NO_MAJORITY

        return None


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
            Event.NO_ACTION: FinishedWithOrdersRound,
        },
        RandomnessRound: {
            Event.DONE: SelectKeeperRound,
            Event.NO_MAJORITY: RandomnessRound,
            Event.ROUND_TIMEOUT: RandomnessRound,
        },
        SelectKeeperRound: {
            Event.DONE: PlaceOrdersRound,
            Event.NO_MAJORITY: RandomnessRound,
            Event.ROUND_TIMEOUT: SelectKeeperRound,
        },
        PlaceOrdersRound: {
            Event.DONE: VerifyExecutionRound,
            Event.ROUND_TIMEOUT: PlaceOrdersRound,
        },
        VerifyExecutionRound: {
            Event.DONE: SelectOrdersRound,
            Event.BAD_SUBMISSION: RandomnessRound,
            Event.NO_MAJORITY: PlaceOrdersRound,
            Event.ROUND_TIMEOUT: PlaceOrdersRound,
        },
        FinishedWithOrdersRound: {},
    }
    final_states: Set[AppState] = {FinishedWithOrdersRound}
    event_to_timeout: EventToTimeout = {
        Event.ROUND_TIMEOUT: 30,
    }
    cross_period_persisted_keys: Set[str] = set()
    db_pre_conditions: Dict[AppState, Set[str]] = {
        SelectOrdersRound: set(),
    }
    db_post_conditions: Dict[AppState, Set[str]] = {
        FinishedWithOrdersRound: set(),
    }
