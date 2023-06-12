"""
Dialogues
"""

from typing import Any

from aea.common import Address
from aea.protocols.base import Message
from aea.protocols.dialogue.base import Dialogue as BaseDialogue
from aea.skills.base import Model

from packages.fetchai.protocols.default.dialogues import \
    DefaultDialogue as BaseDefaultDialogue
from packages.fetchai.protocols.default.dialogues import \
    DefaultDialogues as BaseDefaultDialogues
from packages.valory.protocols.contract_api.dialogues import (
    ContractApiDialogue as BaseContractApiDialogue,
    ContractApiDialogues as BaseContractApiDialogues,
)


ContractApiDialogue = BaseContractApiDialogue
DefaultDialogue = BaseDefaultDialogue


class ContractDialogues(Model, BaseContractApiDialogues):
    """The dialogues class keeps track of all dialogues."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize dialogues."""
        Model.__init__(self, **kwargs)

        def role_from_first_message(  # pylint: disable=unused-argument
            message: Message, receiver_address: Address
        ) -> BaseDialogue.Role:
            """Infer the role of the agent from an incoming/outgoing first message

            :param message: an incoming/outgoing first message
            :param receiver_address: the address of the receiving agent
            :return: The role of the agent
            """
            return ContractApiDialogue.Role.AGENT

        BaseContractApiDialogues.__init__(
            self,
            self_address=str(self.skill_id),
            role_from_first_message=role_from_first_message,
            dialogue_class=ContractApiDialogue,
        )

class DefaultDialogues(Model, BaseDefaultDialogues):
    """The dialogues class keeps track of all dialogues."""

    def __init__(self, **kwargs: Any) -> None:
        """
        Initialize dialogues.

        :return: None
        """
        Model.__init__(self, **kwargs)

        def role_from_first_message(
            message: Message, receiver_address: Address
        ) -> BaseDialogue.Role:
            """Infer the role of the agent from an incoming/outgoing first message

            :param message: an incoming/outgoing first message
            :param receiver_address: the address of the receiving agent
            :return: The role of the agent
            """
            self.context.logger.debug(f"{message} {receiver_address}")
            return DefaultDialogue.Role.AGENT

        BaseDefaultDialogues.__init__(
            self,
            self_address=self.context.agent_address,
            role_from_first_message=role_from_first_message,
        )
