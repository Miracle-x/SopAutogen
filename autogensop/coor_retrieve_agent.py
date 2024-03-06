import chromadb
from autogen import AssistantAgent, Agent
from typing import Dict, Optional, Union, List, Tuple, Any

from autogen.agentchat.contrib.retrieve_assistant_agent import RetrieveAssistantAgent
from autogen.agentchat.contrib.retrieve_user_proxy_agent import RetrieveUserProxyAgent
from autogen.agentchat.contrib.text_analyzer_agent import TextAnalyzerAgent


class CoorRetrieveGoodsAgent(AssistantAgent):
    def __init__(
            self,
            name: str,
            system_message: Optional[str],
            llm_config: Optional[Union[Dict, bool]],
            **kwargs
    ):
        super().__init__(
            name,
            system_message,
            llm_config=llm_config,
            **kwargs
        )

        self.analyzer = TextAnalyzerAgent(llm_config=llm_config)
        self.ragproxyagent = RetrieveUserProxyAgent(
            name="ragproxyagent",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=10,
            retrieve_config={
                "customized_prompt": """You're a retrieve augmented chatbot. You answer user's questions based on the
context provided by the user.
If you can't answer the question with or without the current context , you should reply exactly `UPDATE CONTEXT`.
You must give as complete an answer as possible.

User's question is: {input_question}

Context is: {input_context}
                """,
                "task": 'qa',
                "collection_name": "goods_line",
                "model": self.llm_config["model"],
                "client": chromadb.PersistentClient(path="/tmp/chromadb"),
                "embedding_model": "all-mpnet-base-v2",
                # "get_or_create": False,  # set to True if you want to recreate the collection
                # OPTION： 第一次创建collection启用
                "docs_path": "./autogensop/price&goods_line.txt",  # 一件商品一行
                "get_or_create": True,
                "chunk_mode": "one_line",
                # OPTION： prompt中有few-shots，可启用回答前缀
                # "customized_answer_prefix": 'The answer is'
            },
        )
        self.assistant = RetrieveAssistantAgent(
            name="assistant",
            system_message=self.system_message + "Only return all products that meet the question.",
            # system_message="You are a helpful assistant. Return all products that meet the question. ",
            llm_config={
                # "request_timeout": 600,
                "seed": 42,
                "config_list": self.llm_config['config_list'],
            },
        )
        self.register_reply(Agent, CoorRetrieveGoodsAgent._generate_retrieve_goods_reply)

    def _generate_retrieve_goods_reply(
            self,
            messages: Optional[List[Dict]] = None,
            sender: Optional[Agent] = None,
            config: Optional[Any] = None,
            good_name: Optional[Any] = None,
    ) -> Tuple[bool, Union[str, Dict, None]]:
        if config is None:
            config = self
        if messages is None:
            messages = self._oai_messages[sender]
        # prompt = messages + [{
        #     "role": "system",
        #     "content": "Analyze what product the user wants in the TEXT. Only return the shortest keyword name of the product. ",
        # }]
        # final, good_name = self.generate_oai_reply(prompt)
        # prompt = messages + [{
        #     "role": "system",
        #     "content": f"You can't consider Salesperson needs or generate need out of thin air. Only consider User needs for the {good_name}, the needs like 'besides...' are important. Then ask assistant to return recommended products, which including all user needs, in one question in TEXT's language. Only return that question as short as possible. ",
        # }]
        # final, question = self.generate_oai_reply(prompt)
        print(messages)
        conversation = [message.get("name", "") + ':' + message.get("content", "") + '\n' for message in messages]
        conversation = '\n'.join(conversation)
        # print(conversation)
        if not good_name:
            good_name = self.analyzer.analyze_text(conversation,
                                                   "Analyze what product the user wants in the TEXT. Only return the shortest keyword name of the product. ")
        question = self.analyzer.analyze_text(conversation,
                                              f"You can't consider Salesperson needs or generate need out of thin air. Only consider User needs for the {good_name}. Then ask assistant to return recommended products, which including all user needs, in one question in TEXT's language. Only return that question as short as possible. ")

        self.ragproxyagent.initiate_chat(self.assistant, problem=question, search_string=good_name)
        # ragproxyagent.initiate_chat(assistant, problem=question)
        if self.assistant.last_message()["content"] == "TERMINATE":
            return True, "没有找到您想要的商品，如有其他需要请再告诉我。"
        else:
            return True, self.assistant.last_message()["content"]


class CoorRetrieveQAsAgent(AssistantAgent):
    def __init__(
            self,
            name: str,
            system_message: Optional[str],
            llm_config: Optional[Union[Dict, bool]],
            **kwargs
    ):
        super().__init__(
            name,
            system_message,
            llm_config=llm_config,
            **kwargs
        )
        self.register_reply(Agent, CoorRetrieveQAsAgent._generate_retrieve_qas_reply)

    def _generate_retrieve_qas_reply(
            self,
            messages: Optional[List[Dict]] = None,
            sender: Optional[Agent] = None,
            config: Optional[Any] = None,
            good_name: Optional[Any] = None,
    ) -> Tuple[bool, Union[str, Dict, None]]:
        if config is None:
            config = self
        if messages is None:
            messages = self._oai_messages[sender]
        question = messages[-1].get("content", "")
        CUSTOMIZED_RETRIEVE_PROMPT = """You're a retrieve augmented chatbot as seller. You answer user's questions based on your own knowledge and the context provided by the user. You must think step-by-step.
First, please learn the examples in the context.
Context:{input_context}

Second, please answer user's question as seller referring to the best examples. Only return the answer.
User's question:{input_question}
                    """
        ragproxyagent = RetrieveUserProxyAgent(
            name="ragproxyagent",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=10,
            retrieve_config={
                "customized_prompt": CUSTOMIZED_RETRIEVE_PROMPT,
                "task": 'qa',
                "collection_name": "QAs",
                "model": self.llm_config.config_list[0]["model"],
                "client": chromadb.PersistentClient(path="/tmp/chromadb"),
                "embedding_model": "all-mpnet-base-v2",
                "get_or_create": True,  # set to True if you want to recreate the collection
                # OPTION： get_or_create为True, 第一次创建collection启用,
                "docs_path": "./autogensop/QAs.txt",
                "chunk_mode": "multi_lines",
                "must_break_at_empty_line": True,
                # OPTION： prompt中有few-shots，可启用回答前缀
                # "customized_answer_prefix": 'The answer is'
            },
        )
        assistant = RetrieveAssistantAgent(
            name="assistant",
            system_message="You are a helpful assistant. ",
            llm_config={
                # "request_timeout": 600,
                "seed": 42,
                "config_list": self.llm_config.config_list,
            },
        )
        ragproxyagent.initiate_chat(assistant, problem=question, search_string=good_name)
        return True, assistant.last_message()["content"]
