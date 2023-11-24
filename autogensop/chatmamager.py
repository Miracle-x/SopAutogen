from dataclasses import dataclass
import sys
from typing import Dict, List, Optional, Union
import logging

from autogen import Agent, ConversableAgent

logger = logging.getLogger(__name__)


@dataclass
class GroupChat:
    """A group chat class that contains the following data fields:
    - agents: a list of participating agents.
    - messages: a list of messages in the group chat.
    - max_round: the maximum number of rounds.
    - admin_name: the name of the admin agent if there is one. Default is "Admin".
        KeyBoardInterrupt will make the admin agent take over.
    - func_call_filter: whether to enforce function call filter. Default is True.
        When set to True and when a message is a function call suggestion,
        the next speaker will be chosen from an agent which contains the corresponding function name
        in its `function_map`.
    """

    agents: List[Agent]
    messages: List[Dict]
    max_round: int = 10
    admin_name: str = "Admin"
    func_call_filter: bool = True

    @property
    def agent_names(self) -> List[str]:
        """Return the names of the agents in the group chat."""
        return [agent.name for agent in self.agents]

    def reset(self):
        """Reset the group chat."""
        self.messages.clear()

    def agent_by_name(self, name: str) -> Agent:
        """Find the next speaker based on the message."""
        return self.agents[self.agent_names.index(name)]

    def next_agent(self, agent: Agent, agents: List[Agent]) -> Agent:
        """Return the next agent in the list."""
        if agents == self.agents:
            return agents[(self.agent_names.index(agent.name) + 1) % len(agents)]
        else:
            offset = self.agent_names.index(agent.name) + 1
            for i in range(len(self.agents)):
                if self.agents[(offset + i) % len(self.agents)] in agents:
                    return self.agents[(offset + i) % len(self.agents)]

    def select_speaker_msg(self, agents: List[Agent]):
        """Return the message for selecting the next speaker."""
        return f"""You are in a role play game. The following roles are available:
{self._participant_roles()}.
Ignoring the order in which the above roles appear.
Think about the dependency relationships between different roles. 
Read the following conversation.
Then select the next role from {[agent.name for agent in agents]} to play. Only return the role."""

    def select_speaker(self, last_speaker: Agent, selector: ConversableAgent):
        """Select the next speaker."""
        if self.func_call_filter and self.messages and "function_call" in self.messages[-1]:
            # find agents with the right function_map which contains the function name
            agents = [
                agent for agent in self.agents if agent.can_execute_function(self.messages[-1]["function_call"]["name"])
            ]
            if len(agents) == 1:
                # only one agent can execute the function
                return agents[0]
            elif not agents:
                # find all the agents with function_map
                agents = [agent for agent in self.agents if agent.function_map]
                if len(agents) == 1:
                    return agents[0]
                elif not agents:
                    raise ValueError(
                        f"No agent can execute the function {self.messages[-1]['name']}. "
                        "Please check the function_map of the agents."
                    )
        else:
            agents = self.agents
            # Warn if GroupChat is underpopulated
            n_agents = len(agents)
            if n_agents < 3:
                logger.warning(
                    f"GroupChat is underpopulated with {n_agents} agents. Direct communication would be more efficient."
                )
        selector.update_system_message(self.select_speaker_msg(agents))
        final, name = selector.generate_oai_reply(
            # 根据前五次对话选择下一个发言人
            self.messages[-5:]
            + [
                {
                    "role": "system",
                    "content": f"Read the above conversation. Then select the next role from {[agent.name for agent in agents]} to play. Only return the role.",
                }
            ]
        )
        if not final:
            # i = self._random.randint(0, len(self._agent_names) - 1)  # randomly pick an id
            return self.next_agent(last_speaker, agents)
        try:
            return self.agent_by_name(name)
        except ValueError:
            return self.next_agent(last_speaker, agents)

    def _participant_roles(self):
        return "\n".join([f"{agent.name}: {agent.system_message}" for agent in self.agents])


class GroupChatManager(ConversableAgent):
    """(In preview) A chat manager agent that can manage a group chat of multiple agents."""

    def __init__(
            self,
            groupchat: GroupChat,
            name: Optional[str] = "chat_manager",
            # unlimited consecutive auto reply by default
            max_consecutive_auto_reply: Optional[int] = sys.maxsize,
            human_input_mode: Optional[str] = "NEVER",
            system_message: Optional[str] = "Group chat manager.",
            # seed: Optional[int] = 4,
            task: Optional[str] = "",
            user_name: Optional[str] = "",
            **kwargs,
    ):
        super().__init__(
            name=name,
            max_consecutive_auto_reply=max_consecutive_auto_reply,
            human_input_mode=human_input_mode,
            system_message=system_message,
            **kwargs,
        )
        self.groupchat = groupchat
        self.task = task
        self.user_name = user_name
        self.update_system_message(self.groupchat.select_speaker_msg(self.groupchat.agents))
        self.register_reply(Agent, GroupChatManager.run_chat, config=groupchat)
        # self._random = random.Random(seed)

    # 弃用，因为用户可能有自己的对话节奏，这种任务完成再跳出state循环的做法无法适应用户节奏。改用每次用户输入后新判断state
    # def judge_task_reached(self):
    #     # 判断task是否完成
    #     states_rule = f"""The task is '{self.task}'. Read the above conversation. Think about whether the task is complete, only answer yes or no"""
    #     prompt = self.groupchat.messages + [{
    #         "role": "system",
    #         "content": states_rule,
    #     }]
    #     print('【判断task是否完成】')
    #     final, answer = self.generate_oai_reply(prompt)
    #     if final:
    #         if answer in ['yes', 'yes.', 'Yes', 'Yes.']:
    #             print('************task完成************\n')
    #             return True
    #         elif answer in ['no', 'no.', 'No', 'No.']:
    #             print('--------task未完成----------\n')
    #             return False
    #         else:
    #             print('judge_task_reached 未识别')
    #             print(answer)
    #             exit()
    #     else:
    #         print('judge_task_reached 错误')
    #         exit()

    def run_chat(
            self,
            messages: Optional[List[Dict]] = None,
            sender: Optional[Agent] = None,
            config: Optional[GroupChat] = None,
    ) -> Union[str, Dict, None]:
        """Run a group chat."""
        if messages is None:
            messages = self._oai_messages[sender]
        message = messages[-1]
        speaker = sender
        groupchat = self.groupchat
        for i in range(groupchat.max_round):
            # set the name to speaker's name if the role is not function
            if message["role"] != "function":
                message["name"] = speaker.name
            groupchat.messages.append(message)
            # broadcast the message to all agents except the speaker
            for agent in groupchat.agents:
                if agent != speaker:
                    self.send(message, agent, request_reply=False, silent=True)
            if i != 0 and speaker.name == self.user_name:
                break
            if i == groupchat.max_round - 1:
                # the last round
                break
            try:
                # select the next speaker
                print('【选择发言人】')
                speaker = groupchat.select_speaker(speaker, self)
                print('************选择发言的是：' + speaker.name + '**************\n')
                # let the speaker speak
                reply = speaker.generate_reply(sender=self)
            except KeyboardInterrupt:
                # let the admin agent speak if interrupted
                if groupchat.admin_name in groupchat.agent_names:
                    # admin agent is one of the participants
                    speaker = groupchat.agent_by_name(groupchat.admin_name)
                    reply = speaker.generate_reply(sender=self)
                else:
                    # admin agent is not found in the participants
                    raise
            if reply is None:
                exit()
            # 如果是可学习的agent则学习
            if hasattr(speaker, 'learn_from_user_feedback'):
                speaker.learn_from_user_feedback()
            # The speaker sends the message without requesting a reply
            speaker.send(reply, self, request_reply=False)
            message = self.last_message(speaker)
        return True, None
