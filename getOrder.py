import autogen
from autogen.agentchat.contrib.teachable_agent import TeachableAgent

from autogensop.autogensop import AutogenSop
from autogensop.coor_retrieve_agent import CoorRetrieveQAsAgent, CoorRetrieveGoodsAgent

config_list = autogen.config_list_from_json(
    "OAI_CONFIG_LIST",
    filter_dict={
        "model": ["gpt-4-1106-preview"],
    },
)
print(config_list)
llm_config = {"config_list": config_list, "seed": 42}


target = "Salesperson声明下单成功且买家没有放弃购买，或者买家已经阐述了为何不购买的原因。"
states = {
    "初步介绍": {
        "start_condition": """买家首次咨询且没有明确提问时。""",
        "participate_agent_names": ["Salesperson", "User"],
        "sys_msg": {
            "Salesperson": "展示专业实力，提供公司和产品资料（介绍文件、图片、视频、证书等）、展示公司优势（Why Choose Us）、分享客户案例；"},
        "examples": [],
    },
    "确认需求": {
        "start_condition": """1. 用户提供更详细的需求信息，如具体规格、功能要求等；2. 用户描述他们的问题或挑战，并寻求解决方案；3. 用户表达他们的目标和期望，以及对产品或服务的期望效果；4. 用户咨询产品细节""",
        "participate_agent_names": ["User", "Warehouse", "Salesperson"],
        "sys_msg": {
            "Salesperson": "了解客户对产品的要求和应用方式，判断客户所需产品是否为询价产品，按照客户需求和市场推荐合适产品；"},
        "examples": [],
    },
    "完成订单": {
        "start_condition": """用户表示购买某个商品。""",
        "participate_agent_names": ["User", "Warehouse", "Salesperson"],
        "sys_msg": {
            "Salesperson": "仅回复：下单成功；"},
        "examples": [],
    },
    "反思": {
        "start_condition": """用户表示不购买或放弃购买。""",
        "participate_agent_names": ["User", "Salesperson"],
        "sys_msg": {"Salesperson": "复盘沟通过程，反思输单原因，必要时询问用户为什么不选择自己；"},
        "examples": [],
    },
}
user = autogen.UserProxyAgent(
    name="User",
    code_execution_config=False,
    human_input_mode="ALWAYS"
)
salesperson = TeachableAgent(
    name="Salesperson",
    system_message=f"You are a helpful AI salesperson that remembers useful info from prior chats. You can only sell goods from the Warehouse. If User proposed to buy something but Warehouse did't mation that thing, you can't be the next role, you should be the role behind the Warehouse. ",
    llm_config=llm_config,
    teach_config={
        "verbosity": 0,  # 0 for basic info, 1 to add memory operations, 2 for analyzer messages, 3 for memo lists.
        "reset_db": True,  # Set to True to start over with an empty database.
        "path_to_db_dir": "./tmp/notebook/teachable_agent_db",
        # Path to the directory where the database will be stored.
        "recall_threshold": 1.5,  # Higher numbers allow more (but less relevant) memos to be recalled.
    }
)
# TODO: 用QAs初始化salesperson的记忆
warehouse = CoorRetrieveGoodsAgent(
    name="Warehouse",
    system_message=f"If the previous role was User and he proposed to buy something, you must be the next role. You can list the goods. ",
    llm_config=llm_config,
)

sop = AutogenSop(target=target, states=states, agents=[user, salesperson, warehouse], llm_config=llm_config)
sop.init_sop('User')
