import re
from typing import Union

lst: list[Union[str, int]]


str = "AA**BB#@$CC 가나다-123"

new_str = re.sub(r"[^\uAC00-\uD7A30-9a-zA-Z\s]", "", str)
print(new_str)

temp = "V The pines bowed in the wind"
print(temp.encode().isalpha())

A = [1, 2, 3]
B = [4, 5, 6]
C = [7, 8, 9]

for i in zip(A, B, C):
    print(i)

text = ""
if text:
    print("text")
