import autogen
from autogen.agentchat.contrib.text_analyzer_agent import TextAnalyzerAgent

from autogensop.gradio_chat_manager import GroupChat, GroupChatManager


class GradioAutogenSop(autogen.ConversableAgent):
    def __init__(
            self,
            target="",
            states=[],
            agents=[],
            user_name="",
            llm_config={},
            max_user_input=100,
            **kwargs,
    ) -> None:
        super().__init__(
            name="State manager",
            human_input_mode="NEVER",
            llm_config=llm_config,
            system_message="You are a state manager",
            **kwargs,
        )
        self.target = target
        self.states = states
        self.agents = agents
        self.user_name = user_name
        self.llm_config = llm_config
        self.max_user_input = max_user_input
        self.groupchat = autogen.GroupChat(agents, messages=[])
        self.user = self.groupchat.agent_by_name(self.user_name)
        self.manager = GroupChatManager(self.groupchat, llm_config=self.llm_config)
        self.messages = []
        self.state_groupchat = None

    def _state_start_condition(self):
        return "\n".join([f"{key}: {item['start_condition']}" for key, item in self.states.items()])

    def _state_task(self):
        return "\n".join([f"{key}: {item['task']}" for key, item in self.states.items()])

    def judge_target_reached(self):
        # 判断self.target是否满足
        rule = f"""Your judgment condition is {self.target} If the judgment condition is reached, only return: EXIT, else only return: CONTINUE. """
        prompt = self.messages + [{
            "role": "system",
            "content": rule,
        }]
        final, res = self.generate_oai_reply(prompt)
        print('***************target_reached:' + res)
        if final:
            if 'EXIT' in res:
                return True
            else:
                return False
        else:
            print('judge_target_reached 错误')
            exit()

    def select_state(self):
        # 判断进入的state
        states_rule = f"""Your ultimate goal is {self.target} The optional states are as follows:
{self._state_start_condition()}.
        Read the above conversation. Then select the next state from {[key for key in self.states]}. Only return the state."""
        prompt = self.messages[-4:] + [{
            "role": "system",
            "content": states_rule,
        }]
        print('【判断进入的state】')
        print(prompt)
        final, name = self.generate_oai_reply(prompt)
        while name not in list(self.states.keys()):
            prompt += [{
                "role": "system",
                "content": name + "is wrong answer",
            }]
            final, name = self.generate_oai_reply(prompt)
        print('************进入：' + name + '阶段************\n')
        if final:
            return name
        else:
            print('select_state 错误')
            exit()

    def get_response(self, history):
        while True:
            print('【选择发言人】')
            speaker = self.manager.groupchat.select_speaker(self.user, self.manager)
            print('************选择发言的是：' + speaker.name + '**************\n')
            if speaker.name == self.user.name:
                break
            # 如果是可学习的agent则学习
            if hasattr(speaker, 'learn_from_user_feedback'):
                speaker.learn_from_user_feedback()
            reply = speaker.generate_reply(messages=self.messages, sender=self.manager)
            self.manager.broadcast(reply, speaker)
            message = self.manager.chat_messages[self.user][-1]
            message["name"] = speaker.name
            self.messages.append(message)
            self.manager.groupchat.messages = self.messages
            history += [[None, " **" + speaker.name + ":** " + reply]]
            yield history
        yield history

    def ready_response(self, msg, history):
        self.user.send(message=msg, recipient=self.manager, request_reply=False)
        message = self.manager.chat_messages[self.user][-1]
        message["name"] = self.user.name
        self.messages.append(message)
        state_name = self.select_state()
        # 根据state更改参与者的sys_msg，将阶段目标拼接到sys_msg后面
        for agent_name, sys_msg in self.states[state_name]['sys_msg'].items():
            agent = self.groupchat.agent_by_name(agent_name)
            if sys_msg not in agent.system_message:
                agent.update_system_message(agent.system_message + '此阶段你的目标是：' + sys_msg)
        # 创建group chat，继承已有对话
        self.state_groupchat = GroupChat(
            [self.groupchat.agent_by_name(agent_name) for agent_name in
             self.states[state_name]['participate_agent_names']],
            messages=self.messages,
            max_round=4
        )
        self.manager.groupchat = self.state_groupchat
        self.manager.broadcast(msg, self.user)
        return "", history + [[msg, None]]
