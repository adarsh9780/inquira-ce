import json

with open("current_schema.json", "r") as f:
    data = json.load(f)

payload = {
    "filepath": data["filepath"],
    "context": data["context"],
    "columns": []
}

for col in data["columns"]:
    payload["columns"].append({
        "name": col["name"],
        "description": col["description"],
        "data_type": col["data_type"],
        "sample_values": col["sample_values"]
    })

with open("payload.json", "w") as f:
    json.dump(payload, f, indent=2)

print("Payload prepared.")
