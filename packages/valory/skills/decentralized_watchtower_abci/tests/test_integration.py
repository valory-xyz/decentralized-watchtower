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

"""This module contains tests for watchtower skill."""
import inspect
from packages.valory.skills.order_monitoring.handlers import (
    READY_ORDERS as MONITORING_ORDERS_KEY,
    ContractHandler,
)
from packages.valory.skills.cow_orders_abci.behaviours import (
    ORDERS as COW_ORDERS_KEY,
    CowOrdersBaseBehaviour
)


def test_orders_key_match():
    """Test that the orders are the same."""
    assert MONITORING_ORDERS_KEY == COW_ORDERS_KEY


def test_types_match():
    """Test that the types are the same."""
    getter1 = ContractHandler.ready_orders.fget
    getter2 = CowOrdersBaseBehaviour.orders.fget
    assert inspect.signature(getter1).return_annotation == inspect.signature(getter2).return_annotation


