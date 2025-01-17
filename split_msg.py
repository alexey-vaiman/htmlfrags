import argparse
from msg_split import split_message

parser = argparse.ArgumentParser("split_msg")
parser.add_argument("filename")
parser.add_argument("--max-len", "-ml", default=4096, type=int, 
                    help='max length of fragment (default: 4096)')
args = parser.parse_args()
# print(args.filename)
# print(args.max_len)

try:
    file = open(args.filename, 'r')
    content = file.read()
except FileNotFoundError:
    print(f"Филе нот фоунд: \"{args.filename}\"")
    exit(1)

frag_cnt = 0
# result = ''
# print(input)
# print('-----------------------------')
for s in split_message(content, args.max_len):
    frag_cnt += 1
    print(f"-- fragment #{frag_cnt}: {len(s)} chars --")
    print(s)
    # result += s + '\n'
# print('-----------------------------')
# print(result)
