import flask
import hashlib
import json
from time import time


class Blockchain(object):
    first = {}
    def __init__(self):
        self.nodes = set()
        self.chain = []
        self.current_transactions = []
        print("test")

        self.first = self.new_block(previous_hash=1, proof=100)

    def new_block(self, proof , previous_hash=None):
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactins': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1])
        }

        self.current_transactions = []
        self.chain.append(block)
        return block

    @staticmethod
    def hash(block):
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()



if __name__ == "__main__":
    bc = Blockchain()
    print(bc.first)