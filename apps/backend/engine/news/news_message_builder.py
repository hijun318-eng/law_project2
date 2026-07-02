import json

def build_initial_messages(
    prompt: str,
    question: str,
    rewritten_query: str,
):

    return [
        {
            "role": "system",
            "content": prompt
        },
        {
            "role": "user",
            "content":
                f"사용자 질문:\n{question}\n\n"
                f"뉴스 검색 추천 키워드:\n{rewritten_query}"
        }
    ]


def build_observation_message(
    obs: dict,
    rule: str
):

    return {
        "role": "user",
        "content": json.dumps(
            {
                "rule": rule,
                "evidence": obs
            },
            ensure_ascii=False
        )
    }
