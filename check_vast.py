from vastai_sdk import VastAI
import json

client = VastAI(api_key='5cc472dca11a2668361ab56ff39277ba7d8f7b1a087ff52ae6c0b1690cec185c')
try:
    instances = client.show_instances()
    if isinstance(instances, str):
        data = json.loads(instances)
    else:
        data = instances
    if isinstance(data, list):
        for i in data:
            iid = i.get("id", "?")
            state = i.get("cur_state", "?")
            label = i.get("label", "?")
            gpu = i.get("gpu_name", "?")
            host = i.get("ssh_host", "?")
            port = i.get("ssh_port", "?")
            print(f"Instance: {iid} | Status: {state} | Label: {label}")
            print(f"  GPU: {gpu} | SSH: {host}:{port}")
    elif isinstance(data, dict):
        for k, v in data.items():
            print(f"{k}: {str(v)[:200]}")
except Exception as e:
    print(f"Error: {e}")
    try:
        instances = client.show_instances_v1()
        print(f"v1: {str(instances)[:500]}")
    except Exception as e2:
        print(f"v1 Error: {e2}")
