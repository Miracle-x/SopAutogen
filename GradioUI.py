import gradio as gr
import json

import autogen
from autogen import AssistantAgent

from autogensop.gradio_autogen_sop import GradioAutogenSop
from autogensop.coor_retrieve_agent import CoorRetrieveGoodsAgent

llm_config = [{
    "model": "gpt-4-1106-preview",
    "api_key": "输入您自己的<api_key>",
    "base_url": "输入您自己的<base_url>"
}]
llm_dict = {item['model']: item for item in llm_config}


def build_llm_config(value):
    global llm_config
    llm_config = json.loads(value)
    print(llm_config)
    global llm_dict
    llm_dict = {item['model']: item for item in llm_config}
    return llm_config


llm_config_interface = gr.Interface(
    build_llm_config,
    inputs=gr.TextArea(
        label="编辑LLM配置",
        value=json.dumps(llm_config, indent=2),
    ),
    clear_btn=gr.Button(visible=False),
    submit_btn="保存",
    outputs=gr.JSON(value=llm_config, label="已保存的LLM配置"),
    allow_flagging="never"
)

with gr.Blocks() as agent_config_interface:
    agent_types = {
        "AssistantAgent": AssistantAgent,
        "CoorRetrieveGoodsAgent": CoorRetrieveGoodsAgent
    }
    user = autogen.UserProxyAgent(
        name="User",
        code_execution_config=False,
        human_input_mode="ALWAYS"
    )
    salesperson = AssistantAgent(
        name="Salesperson",
        system_message=f"You are a helpful AI salesperson that remembers useful info from prior chats. If User proposed to buy something but Warehouse did't mention that thing, you can't be the next role. ",
        llm_config={"config_list": llm_config},
    )
    # TODO: 用QAs初始化salesperson的记忆
    warehouse = CoorRetrieveGoodsAgent(
        name="Warehouse",
        system_message=f"If the previous role was User and he proposed to buy something, you can return the goods. ",
        llm_config={"config_list": llm_config},
    )
    # salesman = AssistantAgent(
    #     name="salesman",
    #     system_message=f"You are a helpful assistant，你能根据自身知识，给出真实世界的一些商品详细信息。",
    #     llm_config={"config_list": llm_config},
    # )
    assistant = AssistantAgent(
        name="assistant",
        system_message=f"You are a helpful assistant，你能根据用户需求给出解决方案。 ",
        llm_config={"config_list": llm_config},
    )
    agents = [user, salesperson, warehouse, assistant]
    edit_agent_index = 0

    with gr.Row():
        agent_list = gr.Gallery(
            [("./assets/robot.png", item.name) for item in agents] + [("./assets/add.jpg", "Add new agent")],
            columns=4,
            allow_preview=False
        )
        with gr.Column():
            agent_type = gr.Dropdown(agent_types.keys(), label="Agent类型", visible=False)
            agent_name = gr.Textbox(placeholder="填写agent姓名", label="名称", visible=False)
            agent_sys_msg = gr.Textbox(placeholder="填写agent的system message", label="system message", visible=False)
            agent_llm = gr.Dropdown([item["model"] for item in llm_config], label="使用的LLM", visible=False)
            agent_edit_btn = gr.Button("修改", visible=False)
            agent_del_btn = gr.Button("删除", visible=False)
            agent_add_btn = gr.Button("增加此Agent", visible=False)


    def agentChange(evt: gr.SelectData):
        index = evt.index
        global edit_agent_index
        edit_agent_index = index
        if (index > len(agents) - 1):
            agent_type = gr.Dropdown(agent_types.keys(), label="Agent类型", value=list(agent_types.keys())[0],
                                     visible=True)
            agent_name = gr.Textbox(placeholder="填写agent姓名", label="名称", visible=False)
            agent_sys_msg = gr.Textbox(placeholder="填写agent的system message", label="system message", visible=False)
            agent_llm = gr.Dropdown([item["model"] for item in llm_config], label="使用的LLM", visible=False)
            agent_edit_btn = gr.Button("修改", visible=False)
            agent_del_btn = gr.Button("删除", visible=False)
            agent_add_btn = gr.Button("增加此Agent", visible=True)
        elif (index == 0):
            agent_type = gr.Dropdown(["UserProxyAgent"], value="UserProxyAgent", label="Agent类型", visible=True)
            agent_name = gr.Textbox(placeholder="填写agent姓名", label="名称", visible=False)
            agent_sys_msg = gr.Textbox(placeholder="填写agent的system message", label="system message", visible=False)
            agent_llm = gr.Dropdown([item["model"] for item in llm_config], label="使用的LLM", visible=False)
            agent_edit_btn = gr.Button("修改", visible=False)
            agent_del_btn = gr.Button("删除", visible=False)
            agent_add_btn = gr.Button("增加此Agent", visible=False)
        else:
            agent_name = gr.Textbox(placeholder="填写agent姓名", label="名称", value=agents[index].name, visible=True)
            agent_sys_msg = gr.Textbox(placeholder="填写agent的system message", label="system message",
                                       value=agents[index].system_message, visible=True)
            agent_type = gr.Dropdown(
                agent_types.keys(),
                label="Agent类型",
                value=agents[index].__class__.__name__,
                visible=True
            )
            agent_llm = gr.Dropdown(
                [item["model"] for item in llm_config],
                label="使用的LLM",
                value=agents[index].llm_config["config_list"][0]["model"],
                visible=True
            )
            agent_edit_btn = gr.Button("修改", visible=True)
            agent_del_btn = gr.Button("删除", visible=True)
            agent_add_btn = gr.Button("增加此Agent", visible=False)
        return agent_type, agent_name, agent_sys_msg, agent_llm, agent_edit_btn, agent_del_btn, agent_add_btn


    def editBtn(type, name, sys_msg, llm):
        agents[edit_agent_index] = agent_types[type](
            name=name,
            system_message=sys_msg,
            llm_config={"config_list": [llm_dict[llm]]}
        )
        agent_list = gr.Gallery(
            [("./assets/robot.png", item.name) for item in agents] + [("./assets/add.jpg", "Add new agent")],
            columns=4,
            allow_preview=False
        )
        return agent_list


    def delBtn():
        del agents[edit_agent_index]
        agent_list = gr.Gallery(
            [("./assets/robot.png", item.name) for item in agents] + [("./assets/add.jpg", "Add new agent")],
            columns=4,
            allow_preview=False
        )
        agent_edit_btn = gr.Button("修改", visible=False)
        agent_del_btn = gr.Button("删除", visible=False)
        agent_add_btn = gr.Button("增加此Agent", visible=False)
        return agent_list, agent_edit_btn, agent_del_btn, agent_add_btn


    def addBtn(type):
        index = edit_agent_index
        newAgent = agent_types[type](
            name="agent" + str(index + 1),
            system_message="You are a helpful assistant",
            llm_config={"config_list": [llm_config[0]]}
        )
        agents.append(newAgent)
        agent_list = gr.Gallery(
            [("./assets/robot.png", item.name) for item in agents] + [("./assets/add.jpg", "Add new agent")],
            columns=4,
            allow_preview=False
        )
        agent_name = gr.Textbox(placeholder="填写agent姓名", label="名称", value=agents[index].name, visible=True)
        agent_sys_msg = gr.Textbox(placeholder="填写agent的system message", label="system message",
                                   value=agents[index].system_message, visible=True)
        agent_type = gr.Dropdown(
            agent_types.keys(),
            label="Agent类型",
            value=agents[index].__class__.__name__,
            visible=True
        )
        agent_llm = gr.Dropdown(
            [item["model"] for item in llm_config],
            label="使用的LLM",
            value=agents[index].llm_config["config_list"][0]["model"],
            visible=True
        )
        agent_edit_btn = gr.Button("修改", visible=True)
        agent_del_btn = gr.Button("删除", visible=True)
        agent_add_btn = gr.Button("增加此Agent", visible=False)
        return agent_list, agent_type, agent_name, agent_sys_msg, agent_llm, agent_edit_btn, agent_del_btn, agent_add_btn


    agent_list.select(
        agentChange,
        None,
        [agent_type, agent_name, agent_sys_msg, agent_llm, agent_edit_btn, agent_del_btn, agent_add_btn]
    )
    agent_edit_btn.click(
        editBtn,
        [agent_type, agent_name, agent_sys_msg, agent_llm],
        agent_list
    )
    agent_del_btn.click(delBtn, None, [agent_list, agent_edit_btn, agent_del_btn, agent_add_btn])
    agent_add_btn.click(
        addBtn,
        agent_type,
        [agent_list, agent_type, agent_name, agent_sys_msg, agent_llm, agent_edit_btn, agent_del_btn, agent_add_btn]
    )

with gr.Blocks() as sop_config_interface:
    target = "Salesperson声明下单成功且买家没有放弃购买，或者买家已经阐述了为何不购买的原因。"
    states = {
        "初步介绍": {
            "start_condition": """买家首次咨询且没有明确提问时。""",
            "participate_agent_names": ["Salesperson", "User"],
            "sys_msg": {
                "User": "",
                "Salesperson": "引导用户购买百货商品"},
            "examples": [],
        },
        "确认需求": {
            "start_condition": """1. 用户提供更详细的需求信息，如具体规格、功能要求等；2. 用户描述他们的问题或挑战，并寻求解决方案；3. 用户表达他们的目标和期望，以及对产品或服务的期望效果；4. 用户咨询产品细节""",
            "participate_agent_names": ["User", "Warehouse", "Salesperson"],
            "sys_msg": {
                "User": "",
                "Salesperson": "了解客户对产品的要求和应用方式，按照客户需求推荐合适产品；",
                "Warehouse": "用户需要挑选商品时，你将所知道的商品信息全部返回", },
            "examples": [],
        },
        "完成订单": {
            "start_condition": """用户表示购买某个商品。""",
            "participate_agent_names": ["User", "Warehouse", "Salesperson"],
            "sys_msg": {
                "User": "",
                "Salesperson": "仅回复：下单成功；",
                "Warehouse": "", },
            "examples": [],
        },
        "反思": {
            "start_condition": """用户表示不购买或放弃购买。""",
            "participate_agent_names": ["User", "Salesperson"],
            "sys_msg": {
                "User": "",
                "Salesperson": "复盘沟通过程，反思输单原因，必要时询问用户为什么不选择自己；"},
            "examples": [],
        },
    }
    # states = {'明确需求': {'start_condition': '用户没有想要购买某件具体的商品。',
    #                        'participate_agent_names': ['User', 'assistant'],
    #                        'sys_msg': {'User': '', 'assistant': '给出多条建议，帮助用户确定自己的需求。'},
    #                        'examples': []}, '议价': {'start_condition': '用户想要购买某件具体的商品。',
    #                                                  'participate_agent_names': ['User', 'salesman'],
    #                                                  'sys_msg': {'User': '',
    #                                                              'salesman': '在不能亏本的前提下成交，并尽可能赚取更多的钱。'},
    #                                                  'examples': []}}
    sop_llm_set = llm_dict["gpt-4-1106-preview"]
    edit_state_name = ""

    sop_target = gr.Textbox(label="结束条件", info="每当用户输入完毕，判断结束条件是否达成，达成则整个SOP流程结束",
                            value=target)
    sop_llm = gr.Dropdown(
        [item["model"] for item in llm_config],
        label="流程控制LLM",
        info="用此LLM判断SOP所处环节和是否结束",
        value=llm_config[0]["model"]
    )
    with gr.Row():
        state_list = gr.Gallery(
            [("./assets/state.png", key) for key, item in states.items()] + [("./assets/add.jpg", "Add new state")],
            columns=4,
            allow_preview=False
        )
        with gr.Column():
            sop_name = gr.Textbox(placeholder="填写环节名称", label="环节名称", visible=False)
            sop_start_condition = gr.Textbox(placeholder="填写进入此业务环节的条件", label="进入条件", visible=False)
            sop_participate_agent_names = gr.Dropdown([agent.name for agent in agents], label="参与此环节的agents",
                                                      multiselect=True, visible=False)
            sop_sys_msg = gr.TextArea(label="agent任务", info="各agent在此环节的任务，无特殊任务的agent可留白不填写",
                                      visible=False)
            sop_edit_btn = gr.Button("修改", visible=False)
            sop_del_btn = gr.Button("删除", visible=False)
            sop_add_btn = gr.Button("增加此Agent", visible=False)


    def stateChange(evt: gr.SelectData):
        index = evt.index
        if (index > len(states.keys()) - 1):
            sop_name = gr.Textbox(placeholder="填写环节名称", label="环节名称", value="", visible=True)
            sop_start_condition = gr.Textbox(placeholder="填写进入此业务环节的条件", label="进入条件", visible=False)
            sop_participate_agent_names = gr.Dropdown([agent.name for agent in agents], label="参与此环节的agents",
                                                      multiselect=True, visible=False)
            sop_sys_msg = gr.TextArea(label="agent任务", info="各agent在此环节的任务，无特殊任务的agent可留白不填写",
                                      visible=False)
            sop_edit_btn = gr.Button("修改", visible=False)
            sop_del_btn = gr.Button("删除", visible=False)
            sop_add_btn = gr.Button("增加此环节", visible=True)
        else:
            name = list(states.keys())[index]
            global edit_state_name
            edit_state_name = name
            sop_name = gr.Textbox(placeholder="填写环节名称", label="环节名称", value=edit_state_name, visible=True)
            sop_start_condition = gr.Textbox(placeholder="填写进入此业务环节的条件", label="进入条件",
                                             value=states[edit_state_name]["start_condition"], visible=True)
            sop_participate_agent_names = gr.Dropdown([agent.name for agent in agents], label="参与此环节的agents",
                                                      value=states[edit_state_name]["participate_agent_names"],
                                                      multiselect=True, visible=True)
            sop_sys_msg = gr.TextArea(label="agent任务", info="各agent在此环节的任务，无特殊任务的agent可留白不填写",
                                      value=json.dumps(states[edit_state_name]["sys_msg"], indent=2,
                                                       ensure_ascii=False),
                                      visible=True)
            sop_edit_btn = gr.Button("修改", visible=True)
            sop_del_btn = gr.Button("删除", visible=True)
            sop_add_btn = gr.Button("增加此环节", visible=False)
        return sop_name, sop_start_condition, sop_participate_agent_names, sop_sys_msg, sop_edit_btn, sop_del_btn, sop_add_btn


    def participateAgentChange(names):
        new_sys_msg = {}
        for name in names:
            if (name in states[edit_state_name]["sys_msg"].keys()):
                new_sys_msg[name] = states[edit_state_name]["sys_msg"][name]
            else:
                new_sys_msg[name] = ""
        sop_sys_msg = gr.TextArea(label="agent任务", info="各agent在此环节的任务，无特殊任务的agent可留白不填写",
                                  value=json.dumps(new_sys_msg, indent=2, ensure_ascii=False),
                                  visible=True)
        return sop_sys_msg


    def editSopBtn(sop_name, sop_start_condition, sop_participate_agent_names, sop_sys_msg):
        new_state = {}
        global states
        for key, item in states.items():
            if edit_state_name == key:
                new_state[sop_name] = {
                    "start_condition": sop_start_condition,
                    "participate_agent_names": sop_participate_agent_names,
                    "sys_msg": json.loads(sop_sys_msg),
                    "examples": [],
                }
            else:
                new_state[key] = states[key]
        states = new_state
        state_list = gr.Gallery(
            [("./assets/state.png", key) for key, item in states.items()] + [("./assets/add.jpg", "Add new state")],
            columns=4,
            allow_preview=False
        )
        return state_list


    def delSopBtn():
        # TODO:多次删除触发BUG
        del states[edit_state_name]
        state_list = gr.Gallery(
            [("./assets/state.png", key) for key, item in states.items()] + [("./assets/add.jpg", "Add new state")],
            columns=4,
            allow_preview=False
        )
        sop_edit_btn = gr.Button("修改", visible=False)
        sop_del_btn = gr.Button("删除", visible=False)
        sop_add_btn = gr.Button("增加此Agent", visible=False)
        return state_list, sop_edit_btn, sop_del_btn, sop_add_btn


    def addSopBtn(name):
        states[name] = {
            "start_condition": "",
            "participate_agent_names": [],
            "sys_msg": {},
            "examples": [],
        }
        state_list = gr.Gallery(
            [("./assets/state.png", key) for key, item in states.items()] + [("./assets/add.jpg", "Add new state")],
            columns=4,
            allow_preview=False
        )
        sop_start_condition = gr.Textbox(placeholder="填写进入此业务环节的条件", label="进入条件", visible=True)
        sop_participate_agent_names = gr.Dropdown([agent.name for agent in agents], label="参与此环节的agents",
                                                  multiselect=True, visible=True)
        sop_sys_msg = gr.TextArea(label="agent任务", info="各agent在此环节的任务，无特殊任务的agent可留白不填写",
                                  visible=True)
        sop_edit_btn = gr.Button("修改", visible=True)
        sop_del_btn = gr.Button("删除", visible=True)
        sop_add_btn = gr.Button("增加此Agent", visible=False)
        return state_list, sop_start_condition, sop_participate_agent_names, sop_sys_msg, sop_edit_btn, sop_del_btn, sop_add_btn


    def targetInput(value):
        global target
        target = value


    def sopLlmSelect(llm):
        print(llm)
        global sop_llm_set
        sop_llm_set = llm_dict[llm]


    state_list.select(
        stateChange,
        None,
        [sop_name, sop_start_condition, sop_participate_agent_names, sop_sys_msg, sop_edit_btn, sop_del_btn,
         sop_add_btn]
    )
    sop_target.input(targetInput, sop_target)
    sop_llm.select(sopLlmSelect, sop_llm)
    sop_participate_agent_names.change(participateAgentChange, sop_participate_agent_names, sop_sys_msg)
    sop_edit_btn.click(editSopBtn, [sop_name, sop_start_condition, sop_participate_agent_names, sop_sys_msg],
                       state_list)
    sop_del_btn.click(delSopBtn, None, [state_list, sop_edit_btn, sop_del_btn, sop_add_btn])
    sop_add_btn.click(addSopBtn, sop_name,
                      [state_list, sop_start_condition, sop_participate_agent_names, sop_sys_msg, sop_edit_btn,
                       sop_del_btn, sop_add_btn])
    # gr.JSON(label="环节配置", value=states)

with gr.Blocks() as chat_interface:
    start_btn = gr.Button('检查配置并启动SOP', visible=True)
    chatbot = gr.Chatbot(visible=False)
    msg = gr.Textbox(visible=False)
    stop_btn = gr.Button("手动结束SOP", visible=False)
    SOP = GradioAutogenSop(target=target, states=states, agents=agents, user_name=user.name,
                           llm_config={"config_list": [sop_llm_set]})


    def start():
        new_agents = []
        for agent in agents:
            if agent.__class__.__name__ == 'UserProxyAgent':
                new_agents.append(agent)
                print(agent.__dict__)
            else:
                new_agent = agent_types[agent.__class__.__name__](
                    name=agent.name,
                    system_message=agent.system_message,
                    llm_config={"config_list": [llm_dict[agent.llm_config["config_list"][0]["model"]]]}
                )
                del agent
                print(new_agent.__dict__)
                new_agents.append(new_agent)

        global SOP
        SOP = GradioAutogenSop(target=target, states=states, agents=new_agents, user_name=user.name,
                               llm_config={"config_list": [llm_dict[sop_llm_set['model']]]})
        print(SOP.__dict__)
        config_flag = True
        start_btn = gr.Button('检查配置并启动SOP', visible=not config_flag)
        chatbot = gr.Chatbot(visible=config_flag)
        msg = gr.Textbox(visible=config_flag)
        stop_btn = gr.Button("手动结束SOP", visible=config_flag)
        return start_btn, chatbot, msg, stop_btn


    def stop():
        global SOP
        del SOP
        config_flag = False
        start_btn = gr.Button('检查配置并启动SOP', visible=not config_flag)
        chatbot = gr.Chatbot(visible=config_flag, value=[])
        msg = gr.Textbox(visible=config_flag)
        stop_btn = gr.Button("手动结束SOP", visible=config_flag)
        return start_btn, chatbot, msg, stop_btn


    def readyResponse(msg, chatbot):
        global SOP
        return SOP.ready_response(msg, chatbot)


    def getResponse(chatbot):
        global SOP
        f = SOP.get_response(chatbot)
        for item in f:
            yield item


    msg.submit(readyResponse, [msg, chatbot], [msg, chatbot]).then(getResponse, chatbot, chatbot)
    start_btn.click(start, None, [start_btn, chatbot, msg, stop_btn])
    stop_btn.click(stop, None, [start_btn, chatbot, msg, stop_btn])

with gr.Blocks() as app:
    gr.Markdown("### 西北工业大学·高德宏&杨黎斌&胥基")
    gr.TabbedInterface(
        [llm_config_interface, agent_config_interface, sop_config_interface, chat_interface],
        ["配置LLM", "配置Agents", "配置SOP", "开始聊天"],
    )

if __name__ == "__main__":
    app.launch()
