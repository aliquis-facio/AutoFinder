import sys

parentheses = ["<", ">"]


def erase_parentheses():
    pass


with open("./TestText/output.txt", "rt", encoding="utf-8") as f:
    for _ in range(10):
        line = f.readline().split("\t")
        for i in range(len(line)):
            print(f"{i}: {line[i]}")
        print("--- --- --- --- ---")
