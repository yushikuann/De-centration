import hashlib
import json
import requests
from time import time
from uuid import uuid4
from urllib.parse import urlparse
from flask import Flask, jsonify, request

class Blockchain(object):
    def __init__(self):
        self.nodes = set()
        # 用 set 来储存节点，避免重复添加节点.
        self.chain = []
        self.current_transactions = []

        # 创建创世区块
        self.new_block(previous_hash=1, proof=100)

    def reister_node(self, address):
        """
        在节点列表中添加一个新节点
        :param address:
        :return:
        """
        prsed_url = urlparse(address)
        self.nodes.add(prsed_url.netloc)

    def valid_chain(self, chain):
        """
        确定一个给定的区块链是否有效
        :param chain:
        :return:
        """
        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print('{}'.format(last_block))
            print('{}'.format(block))
            print("\n______\n")
            # 检查block的散列是否正确
            if block['previous_hash'] != self.hash(last_block):
                return False
            # 检查工作证明是否正确
            if not self.valid_proof(last_block['proof'], block['proof']):
                return False

            last_block = block
            current_index += 1
        return True

    def ressolve_conflicts(self):
        """
        共识算法
        :return:
        """
        neighbours = self.nodes
        new_chain = None
        # 寻找最长链条
        max_length = len(self.chain)

        # 获取并验证网络中的所有节点的链
        for node in neighbours:
            response = requests.get('http://{}/chain'.format(node))

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                # 检查长度是否长，链是否有效
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        # 如果发现一个新的有效链比当前的长，就替换当前的链
        if new_chain:
            self.chain = new_chain
            return True
        return False

    def new_block(self, proof, previous_hash=None):
        """
        创建一个新的块并将其添加到链中
        :param proof: 由工作证明算法生成证明
        :param previous_hash: 前一个区块的hash值
        :return: 新区块
        """
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }

        # 重置当前交易记录
        self.current_transactions = []

        self.chain.append(block)
        return block

    def new_transaction(self, sender, recipient, amount):
        # 将新事务添加到事务列表中
        """
        Creates a new transaction to go into the next mined Block
        :param sender:发送方的地址
        :param recipient:收信人地址
        :param amount:数量
        :return:保存该事务的块的索引
        """
        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
        })

        return self.last_block['index'] + 1

    @staticmethod
    def hash(block):
        """
        给一个区块生成 SHA-256 值
        :param block:
        :return:
        """
        # 必须确保这个字典（区块）是经过排序的，否则将会得到不一致的散列
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        # 返回链中的最后一个块
        return self.chain[-1]

    def proof_of_work(self, last_proof):
        # 工作算法的简单证明
        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1
        return proof

    @staticmethod
    def valid_proof(last_proof, proof):
        # 验证证明
        guess = ('{}{}'.format(last_proof, proof)).encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"


# 实例化节点
app = Flask(__name__)

# 为该节点生成一个全局惟一的地址
node_identifier = str(uuid4()).replace('-', '')

# 实例化Blockchain类
blockchain = Blockchain()


# 进行挖矿请求
@app.route('/mine', methods=['GET'])
def mine():
    # 运行工作算法的证明来获得下一个证明。
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    # 必须得到一份寻找证据的奖赏。
    blockchain.new_transaction(
        sender="0",
        recipient=node_identifier,
        amount=1,
    )

    # 通过将其添加到链中来构建新的块
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)
    response = {
        'message': "New Block Forged",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }
    return jsonify(response), 200


# 创建交易请求
@app.route('/transactions/new', methods=['POST'])
def new_transactions():
    values = request.get_json()

    # 检查所需要的字段是否位于POST的data中
    required = ['seder', 'recipient', 'amount']
    if not all(k in values for k in request):
        return 'Missing values', 400

    # 创建一个新的事物
    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])
    response = {'message': 'Transaction will be added to Block {}'.format(index)}
    return jsonify(response), 201


# 获取所有快信息
@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200


# 添加节点
@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()
    nodes = values.get('nodes')
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201


# 解决冲突
@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain.chain
        }

    return jsonify(response), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)



'''
类 BlockChain分析:
构造函数：

创建一个变量nodes来存储所有的节点(保证节点之间互不相同)
创建一个变量chain来存储链
调用new_block函数创建创世块(设置初始hash值(创世块的previous hash), 检验值设置为100)
hash函数(static method):

将整个块的转成一个string,，然后再通过这个string生成hash值，并转成16进制
值得称赞的是，这里要确保通过json将dict转成string的过程中，需要保证keys的顺序。只有这样，才能确保整个hash映射到整个块的时候，得到的结果具有唯一性
last_block函数(通过@property操作符变成了一个属性)

会返回这个blockChain中最后一个块
valid_proof证明函数

传进来的两个检验值，一个是last_proof 还有一个就是proof。
在直接放在一起之后，通过哈希映射之中的sha256映射(再转16进制)
最后，通过判断上面得到的最终的哈希值来判断前4位是不是都是0
如果4个0开头，那么就是合法，否者就是不合法的
proof_of_work函数

通过传进来的那个函数中的参数(也就是前一个的proof值)
通过循环来逐步找到对应的当前proof使得上面的valid_proof函数返回的是一个true值
reister_node()函数

传进来的参数为address,表示地址。
这个参数必须是网页url，或者是对应的ip地址。
经过解析之后，节点的命名就是一个ip地址或者是网页地址（网络层面上跟ip地址等价）
valid_chain()函数

这里会传进来一个chain 可以理解为一个列表之类的可遍历的对象。
然后判断后一个块的previous_hash是不是真的就是前一个块做了hash的结果
同时也需要判断，这个检验值是否合法
直到这些都满足之后，才算是ok的
new_block函数：

创建一个新的块。语言层面上，其实就是一个字典。每个块存储的交易都是整个类一开始就公有的
index设置为链长度+1
‘previous_hash’:previous_hash or self.hash(self.chain[-1]) 这个地方有点意思。
如果是创世块，这里就会直接得到对应的结果
ressolve_conflicts函数：

先循环检验每个节点。来进行判断
要求子节点存储的长度要小于总长度
要求子节点存储的链也必须是合法的
如果有合法的，并且子节点上的链长度更长那就复制给main服务器
如果发生过改变，就返回True
else return false
'''