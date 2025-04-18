"""
工作流模块：定义和构建代理工作流图
"""
from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph

from src.agents.portfolio_manager import portfolio_management_agent
from src.agents.risk_manager import risk_management_agent
from src.utils.analysts import get_analyst_nodes
from src.graph.state import AgentState


def start(state: AgentState):
    """使用输入消息初始化工作流。"""
    return state


def create_workflow(selected_analysts=None, show_reasoning=False):
    """创建使用选定分析师的工作流。

    Args:
        selected_analysts: 选定的分析师名称列表，如果为None，使用所有分析师
        show_reasoning: 是否显示分析师推理过程

    Returns:
        StateGraph: 配置好的工作流图
    """
    workflow = StateGraph(AgentState)
    workflow.add_node("start_node", start)

    # 从配置中获取分析师节点
    analyst_nodes = get_analyst_nodes()

    # 如果未选择分析师，默认使用全部
    if selected_analysts is None:
        selected_analysts = list(analyst_nodes.keys())
    
    # 添加选定的分析师节点
    for analyst_key in selected_analysts:
        if analyst_key in analyst_nodes:
            node_name, node_func = analyst_nodes[analyst_key]
            workflow.add_node(node_name, node_func)
            workflow.add_edge("start_node", node_name)

    # 始终添加风险和投资组合管理
    workflow.add_node("risk_management_agent", risk_management_agent)
    workflow.add_node("portfolio_management_agent", portfolio_management_agent)

    # 将选定的分析师连接到风险管理
    for analyst_key in selected_analysts:
        if analyst_key in analyst_nodes:
            node_name = analyst_nodes[analyst_key][0]
            workflow.add_edge(node_name, "risk_management_agent")

    workflow.add_edge("risk_management_agent", "portfolio_management_agent")
    workflow.add_edge("portfolio_management_agent", END)

    workflow.set_entry_point("start_node")
    return workflow


# 为了保持与测试兼容性，添加别名
build_workflow = create_workflow 