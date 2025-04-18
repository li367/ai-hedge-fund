"""
测试导入是否正常工作
"""
try:
    import questionary
    print("questionary 导入成功")
except ImportError as e:
    print(f"questionary 导入失败: {e}")

try:
    import langgraph.graph
    print("langgraph.graph 导入成功")
except ImportError as e:
    print(f"langgraph.graph 导入失败: {e}")

print("测试完成") 