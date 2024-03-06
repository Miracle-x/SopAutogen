import autogen
from autogen.agentchat.contrib.text_analyzer_agent import TextAnalyzerAgent

from autogensop.chatmamager import GroupChat, GroupChatManager


# 因为用户可能有自己的对话节奏，这种任务完成再跳出state循环的做法无法适应用户节奏。改用每次用户输入后新判断state
# 根据用户的输入驱动，用户输入不同的内容，流程前进方向会改变
# 基于一个state任务task建立一个GroupChat，GroupChat包含一个ChatManager、多个agent、一个User
# ChatManager：决定跟哪个agent对话（用户根据预设模式介入）
# agent：只根据ChatManager的提问回答
# User：模式介入


# 开始对话
# 1. ChatManager获取除User外所有agent能力
# 2. ChatManager向用户介绍自己融合其他agents后的能力，询问需求
# 3. User告诉ChatManager自己的input
# 4. 检查是否target拥有且满足，是则结束，否则进入5.
# 5. ChatManager决定处于哪个state
# 6. ChatManager根据target、task、input、history（可选）决定跟User或哪个agent对话，直至轮到User发言，进入3.

class AutogenSop(autogen.ConversableAgent):
    """
    使用autogen为agent的SOP流程控制
    """

    # 传入config_path，根据文件配置初始化
    def __init__(
            self,
            target,
            states,
            agents,
            llm_config,
            max_user_input = 100,
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
        self.llm_config = llm_config
        self.max_user_input = max_user_input
        self.groupchat = autogen.GroupChat(agents, messages=[])
        self.messages = []

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
        final, name = self.generate_oai_reply(prompt)
        print('************进入：' + name + '阶段************\n')
        if final:
            return name
        else:
            print('select_state 错误')
            exit()

    def init_sop(self, user_name):
        user = self.groupchat.agent_by_name(user_name)
        self.stop_reply_at_receive(user)
        self.send(message="请问有什么需要帮助吗?", recipient=user, request_reply=True)
        last_msg = self.last_message()
        last_msg['name'] = user_name
        self.messages.append(last_msg)
        self.max_user_input -= 1

        manager = GroupChatManager(self.groupchat, user_name=user_name, llm_config=self.llm_config)
        while not self.judge_target_reached() and self.max_user_input > 0:
            # 获取最后一条发言者
            last_speaker = self.groupchat.agent_by_name(self.messages[-1]['name'])
            last_message = self.messages[-1]['content']

            # 判断state
            if last_speaker.name == user_name:
                state_name = self.select_state()

            # 根据state更改参与者的sys_msg，将阶段目标拼接到sys_msg后面
            for agent_name, sys_msg in self.states[state_name]['sys_msg'].items():
                agent = self.groupchat.agent_by_name(agent_name)
                if sys_msg not in agent.system_message:
                    agent.update_system_message(agent.system_message + '此阶段你的目标是：' + sys_msg)

            # 创建group chat，继承已有对话
            groupchat = GroupChat(
                [self.groupchat.agent_by_name(agent_name) for agent_name in
                 self.states[state_name]['participate_agent_names']],
                messages=self.messages[:-1],
                max_round=4
            )
            manager.groupchat = groupchat
            if len(self.messages) <= 1:
                last_speaker.initiate_chat(
                    message=last_message, recipient=manager, clear_history=False
                )
            elif len(self.messages) > 1:
                manager.generate_reply(messages=manager.chat_messages[last_speaker], sender=last_speaker)
            self.messages = groupchat.messages

            self.max_user_input -= 1
