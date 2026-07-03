import re


def normalize_law_name(name: str):
    return re.sub(r"\s+", "", name.strip())


def normalize_article_no(no: str):
    no = re.sub(r"\s+", "", no.strip())
    if not no.startswith("제"):
        no = "제" + no
    return no
