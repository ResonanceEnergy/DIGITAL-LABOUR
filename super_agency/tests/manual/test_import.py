import sys, os
root=os.getcwd()
sys.path.insert(0, os.path.join(root, 'inner_council'))
print('sys.path prefix', sys.path[:3])
try:
    import agents.base_agent
    print('agents.base_agent imported', agents.base_agent)
except Exception as e:
    print('import error', e)
