import autogen
from autogensop.autogensop import AutogenSop
# 如果要更改调用的模型，参考
# https://microsoft.github.io/autogen/blog/2023/07/14/Local-LLMs

# 此示例的一些超参
MAX_CONSECUTIVE_AUTO_REPLY = 5
ATTRIBUTE = {
    "颜色": "",
    "尺寸": "",
    "材料": "",
}

# llm配置：dict，详见
# https://microsoft.github.io/autogen/docs/FAQ#use-the-constructed-configuration-list-in-agents
config_list = autogen.config_list_from_json(
    "OAI_CONFIG_LIST",
    filter_dict={
        "model": ["gpt-4-1106-preview"],
    },
)
llm_config = {"config_list": config_list, "seed": 42}

# 一个跳出循环的条件，也是SOP的最终目标：string
target = "Salesperson说过“谢谢您提供的信息，我们会尽快为您回复。”"

# SOP的各个阶段：dict
states = {
    # state名称：dict
    "第一轮交互": {
        "start_condition": """买家首次咨询。""",  # 进入此state的条件
        "participate_agent_names": ["Salesperson", "User"],  # 参与此state的agent
        # 此阶段每个agent的系统提示，会拼接到agent.system_message的后面。关于system_message详见
        # https://platform.openai.com/docs/guides/prompt-engineering/tactic-ask-the-model-to-adopt-a-persona
        # agent名称：string
        "sys_msg": {
            "Salesperson": """XXX需要你替换为合适的词。你的话术是：“感谢您对XXX感兴趣，主人不在，我是智能接待机器人小宝，可以请您提供对XXX、XXX方面的需求么，以便主人上线后给您提供更加精准的报价。”"""
        },
        # 暂时没有用到
        # TODO：将examples作为此阶段交流示例，让llm学习后再与用户交互
        "examples": [],
    },
    "第n轮交互": {
        "start_condition": """用户尚未对""" + '、'.join(ATTRIBUTE.keys()) + """中的某个做出需求描述""",
        "participate_agent_names": ["User", "Salesperson"],
        "sys_msg": {
            "Salesperson": """XXX需要你替换为合适的词。你的话术是：“谢谢您提供的信息，可以请您再提供对XXX方面的需求吗？”"""
        },
        "examples": [],
    },
    "最后一轮交互": {
        "start_condition": """用户对""" + '、'.join(ATTRIBUTE.keys()) + """中的每个属性都提出了需求描述""",
        "participate_agent_names": ["User", "Salesperson"],
        "sys_msg": {"Salesperson": "不要加其他任何东西，仅仅回答：”谢谢您提供的信息，我们会尽快为您回复。“"},
        "examples": [],
    },
}

# 此处实例化参与SOP的所有agent，参考如下网址。
# https://microsoft.github.io/autogen/docs/reference/agentchat/conversable_agent
# 在目录 Reference -> agentchat 下的所有agent都可用，还可根据自己的需求自定义agent类，例如本项目目录 autogensop -> coor_retrieve_agent.py 中定义的CoorRetrieveGoodsAgent类

# 用户agent，详见
# https://microsoft.github.io/autogen/docs/reference/agentchat/user_proxy_agent
user = autogen.UserProxyAgent(
    name="User",
    code_execution_config=False,
    human_input_mode="ALWAYS"
)
# 助手agent，详见
# https://microsoft.github.io/autogen/docs/reference/agentchat/assistant_agent
salesperson = autogen.AssistantAgent(
    name="Salesperson",
    system_message=f"你是一个主动的AI助手，会灵活且合理的运用话术，你需要提取对话中用户对" + '、'.join(
        ATTRIBUTE.keys()) + "的描述。如果对话中缺少对其中某个的描述，你需要主动提问该信息，尽量像一个真正的人。",
    llm_config=llm_config,
)

# 实例化SOP对象
sop = AutogenSop(
    target=target,  # 一个跳出循环的条件，也是SOP的最终目标：string
    states=states,  # SOP的各个阶段：dict
    agents=[user, salesperson],  # 参与SOP的所有agent：list[agent]
    llm_config=llm_config,  # llm配置：dict
    max_user_input=MAX_CONSECUTIVE_AUTO_REPLY  # 最大交互次数（用户每发言一次计为交互一次）：int
)

# 调用SOP对象的init_sop方法，传入用户名称来初始化对话
sop.init_sop(user_name='User')
