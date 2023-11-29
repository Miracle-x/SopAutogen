import autogen
from autogen.agentchat.contrib.teachable_agent import TeachableAgent
from autogensop.autogensop import AutogenSop

MAX_CONSECUTIVE_AUTO_REPLY = 5
ATTRIBUTE = {
    "颜色": "",
    "尺寸": "",
    "材料": "",
}

config_list = autogen.config_list_from_json(
    "OAI_CONFIG_LIST",
    filter_dict={
        "model": ["gpt-4-1106-preview"],
    },
)
llm_config = {"config_list": config_list, "seed": 42}

target = "Salesperson说过“谢谢您提供的信息，我们会尽快为您回复。”"
states = {
    "第一轮交互": {
        "start_condition": """买家首次咨询。""",
        "next_state_prompt": """""",
        "participate_agent_names": ["Salesperson", "User"],
        "sys_msg": {
            "Salesperson": """XXX需要你替换为合适的词。你的话术是：“感谢您对XXX感兴趣，主人不在，我是智能接待机器人小宝，可以请您提供对XXX、XXX方面的需求么，以便主人上线后给您提供更加精准的报价。”"""
        },
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
user = autogen.UserProxyAgent(
    name="User",
    code_execution_config=False,
    human_input_mode="ALWAYS"
)
salesperson = autogen.AssistantAgent(
    name="Salesperson",
    system_message=f"你是一个主动的AI助手，会灵活且合理的运用话术，你需要提取对话中用户对" + '、'.join(
        ATTRIBUTE.keys()) + "的描述。如果对话中缺少对其中某个的描述，你需要主动提问该信息，尽量像一个真正的人。",
    llm_config=llm_config,
)
# salesperson = TeachableAgent(
#     name="Salesperson",
#     system_message=f"你是一个主动的AI助手，你需要提取对话中用户对" + '、'.join(
#         ATTRIBUTE.keys()) + "的描述。如果对话中缺少对其中某个的描述，你需要主动提问该信息；如果已提取到所有描述，则仅返回：EXIT",
#     llm_config=llm_config,
#     teach_config={
#         "verbosity": 0,  # 0 for basic info, 1 to add memory operations, 2 for analyzer messages, 3 for memo lists.
#         "reset_db": True,  # Set to True to start over with an empty database.
#         "path_to_db_dir": "./tmp/notebook/teachable_agent_db",
#         # Path to the directory where the database will be stored.
#         "recall_threshold": 1.5,  # Higher numbers allow more (but less relevant) memos to be recalled.
#     }
# )

sop = AutogenSop(target=target, states=states, agents=[user, salesperson], llm_config=llm_config,
                 max_user_input=MAX_CONSECUTIVE_AUTO_REPLY)
sop.init_sop('User')
