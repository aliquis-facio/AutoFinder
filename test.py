import re
from typing import Union

lst: list[Union[str, int]]


str = "AA**BB#@$CC 가나다-123"

new_str = re.sub(r"[^\uAC00-\uD7A30-9a-zA-Z\s]", "", str)
print(new_str)
