import sys
from lamb.lamb import vLLMLamb

try:
    with open(sys.argv[1], 'r') as f:
        input_code = f.read()
except:
    raise FileNotFoundError()

lamb_vllm_agent = vLLMLamb(
    model = 'meta-llama/Llama-3.1-8B-Instruct',
    host = '127.0.0.1',
    port = 8080,
    verbose = True
)

output_code = lamb_vllm_agent.migrate(input_code)

print(output_code)