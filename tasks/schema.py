# 고정 출력 용
skip_logic_schema = {
    "name": "skip_logic",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["items"],
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["start", "end", "value"],
                    "properties": {
                        "start": {"type": "string"},
                        "end": {"type": "string"},
                        "value": {"type": "integer"},
                    },
                },
            }
        },
    },
}