import sys
from lamb import OpenAILamb

try:
    with open(sys.argv[1], 'r') as f:
        input_code = f.read()
except:
    raise FileNotFoundError()

lamb_openai_agent = OpenAILamb(
    model = 'o3-mini',
    api_key = '',
    verbose = True
)

output_code = lamb_openai_agent.migrate(input_code)

print(output_code)