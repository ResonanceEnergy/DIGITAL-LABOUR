with open(r'C:\Dev\DIGITAL-LABOUR\agents\cto_agent.py','r') as f:
    for i,line in enumerate(f,1):
        if 260 <= i <= 275:
            print(i,repr(line))
