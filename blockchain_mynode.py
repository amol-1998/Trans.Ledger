import datetime
import hashlib
import json
from flask import Flask, jsonify, request, render_template, redirect, url_for
from uuid import uuid4
import requests
from urllib.parse import urlparse


# Building the Blockchain
class Blockchain:
    def __init__(self):
        self.chain = []
        self.transactions = [{'sender': '-', 'receiver': '-', 'amount': '0'}]  # This is the list of transcations that the block will contain
        self.create_block(proof=1, previous_hash='0')
        self.nodes = set() # This is the set of nodes our node is connected to

    def create_block(self, proof, previous_hash):
        # This function structures the block and adds it to the blockchain
        block = {
                'index': len(self.chain) + 1,
                'timestamp': str(datetime.datetime.now()),
                'proof': proof,
                'previous_hash': previous_hash,
                'transactions': self.transactions
                }
        self.transactions = [] # Because once the transactions are added to a block, new transactions will be added to this list
        self.chain.append(block)
        return block
        # The block is returned so that it can display the information in postman

    def get_previous_block(self):
        return self.chain[-1]

    # This function basically returns a number as a proof that the miner has done some work in solving the given problem
    # The problem could be anything but the result hash should be lower than the predefined value
    # The cryptographic puzzle is usually defined as: Find the nonce such that .... should be lower than target
    def proof_of_work(self, previous_proof):
        new_proof = 1
        check_proof = False
        while check_proof is False:
            # This is the cryptographic problem
            hash_value = hashlib.sha256(str(new_proof**2 - previous_proof**2).encode()).hexdigest()
            if hash_value[:4] == '0000':
                check_proof = True
            else:
                new_proof += 1
        return new_proof

    # This function returns the hash of the block
    def hash_block(self,block):
        encoded_block = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(encoded_block).hexdigest()

    # This function checks whther the chain is valid or not by checking 2 things:
    # 1. The previous_hash of each block is equal to the hash of the previous block
    # 2. The proof of each block is valid
    def is_chain_valid(self, chain):
        length = len(chain)
        i = 1
        previous_block_proof = chain[0]['proof'] # This is the proof of the Genesis Block which is 1
        while i < length:
            current_hash = chain[i]['previous_hash'] # Current Block's previous hash - starting from 1
            prev_block_hash = self.hash_block(chain[i-1]) # Hash of the previous block
            # Matching the HASH LINKS
            if prev_block_hash != current_hash:
                return False

            # Validating the Proofs
            current_block_proof = chain[i]['proof'] # Proof of the current block - starting from 1
            hash_value = hashlib.sha256(str(current_block_proof**2 - previous_block_proof**2).encode()).hexdigest()
            if hash_value[:4] != '0000':
                return False
            previous_block_proof = current_block_proof
            i +=1
        return True

    def add_transaction(self, sender, receiver, amount):
        self.transactions.append({'sender':sender,
                                  'receiver': receiver,
                                  'amount': amount})
        # This function returns the index of the new mined block which'll contain these transactions
        previous_block = self.get_previous_block()
        return previous_block['index'] + 1

    def add_node(self, node_address):
        parsed_address = urlparse(node_address)  # This function parses a URL into 6 components i.e. returns a 6-tuple
        self.nodes.add(parsed_address.netloc)  # netloc is the domain name from the URL
        # 6-tuple returned is of the format:    scheme://netloc/path;parameters?query#fragment

    # This function replaces the chain of the node that calls this function
    # This function returns true if the chain at this node is replaced, else false
    def replace_chain(self):
        network_nodes = self.nodes
        longest_chain = None
        max_length = len(self.chain)
        for node in network_nodes:
            response = requests.get(f'http://{node}/get_bc')
            if response.status_code == 200:
                node_chain = response.json()['Blockchain']  # json() function converts a dictionary to json string
                node_chain_length = response.json()['Length']  # ATTENTION HERE
                if node_chain_length > max_length and self.is_chain_valid(node_chain):
                    longest_chain = node_chain
                    max_length = node_chain_length
        if longest_chain:
            self.chain = longest_chain
            return True
        return False


# Creating the Flask WebApp
web_app = Flask(__name__, template_folder='templates')

# uuid4 stands for universal unique identifier.
# It generates random id's of 128 bits on the basis of time, hardware (MAC etc.)
# Here it is used to generate a unique id for the current node viz. 127.0.0.1:5000
node_address_id = str(uuid4()).replace('-', '')

blockchain = Blockchain()

user_logged_in = False

error = False

username = None

@web_app.route('/', methods=['GET','POST'])
def index():
    global user_logged_in
    global error
    global username
    if request.method == 'POST':
        username = request.form['username']
        pwd = request.form['pwd']
        if username == 'amol_1998' and pwd == 'Amol$123':
            user_logged_in = True
            error = False
            return render_template('index.html', user_logged_in=user_logged_in, error=error, username=username)  # Basically call this function again to render the template
        else:
            error = True
            return render_template('index.html', user_logged_in=user_logged_in, error=error, username=username)
    return render_template('index.html', user_logged_in=user_logged_in, error=error, username=username)


# Mining a Block - This URL is used to manually mine a block with default sender, receiver and amount
'''
@web_app.route('/mine_block', methods=['GET'])
def mine_block():
    previous_block = blockchain.get_previous_block()
    previous_block_proof = previous_block['proof'] # Previous_block_proof is found to find the current block proof
    new_block_proof = blockchain.proof_of_work(previous_block_proof)
    previous_hash = blockchain.hash_block(previous_block) # This is the hash of the previous block i.e. the last block
    # This function adds a transaction to the list of transactions
    blockchain.add_transaction(sender=node_address_id, receiver='NODE 1', amount=1)
    newly_created_block = blockchain.create_block(new_block_proof, previous_hash)
    response = {'index':newly_created_block['index'],
                'timestamp': newly_created_block['timestamp'],
                'proof': newly_created_block['proof'],
                'previous_hash': newly_created_block['previous_hash'],
                'transactions': newly_created_block['transactions']}
    return jsonify(response), 200
'''


@web_app.route('/logout',methods=['GET'])
def logout():
    global user_logged_in
    global error
    global username
    user_logged_in = False
    error = False
    username = None
    return redirect(url_for('index'))


@web_app.route('/add_transaction', methods=['GET', 'POST'])
def add_transaction():

    global user_logged_in
    if user_logged_in is False:
        return redirect(url_for('index'))

    if request.method == 'POST':
        # Following Lines find the proof of new block and hash of previous block
        previous_block = blockchain.get_previous_block()
        previous_block_proof = previous_block['proof']  # Previous_block_proof is found to find the current block proof
        new_block_proof = blockchain.proof_of_work(previous_block_proof)
        previous_hash = blockchain.hash_block(previous_block)  # This is the hash of the previous block i.e. the last block

        # Following lines find the entered sender , receiver adn amount
        # And add the given transaction to the list of transactions
        sender = str(request.form['sender']).strip()
        receiver = str(request.form['receiver']).strip()
        amount = str(request.form['amount']).strip()
        blockchain.add_transaction(sender, receiver, amount)

        # Here we create a new block and append it to our chain
        blockchain.create_block(new_block_proof, previous_hash)

        return redirect(url_for('index'))

    return render_template('add_transaction.html', username=username)

#  This URL returns the blockchain of the node for consensus
@web_app.route('/get_bc',methods=['GET'])
def get_bc():
    global user_logged_in
    if user_logged_in is False:
        return redirect(url_for('index'))
    
    chain = blockchain.chain
    response = {'Blockchain':chain,
                'Length': len(chain)}
    return jsonify(response), 200


@web_app.route('/get_transactions', methods=['GET'])
def get_transactions():
    global user_logged_in
    if user_logged_in is False:
        return redirect(url_for('index'))
    lis_trans = []
    blockchain.replace_chain()
    chain = blockchain.chain
    for x in chain:
        t = x['transactions']
        if len(t) == 0:
            continue
        lis_trans.append(x)
    #print(lis_trans)
    return render_template('get_transactions.html', chain=lis_trans, username=username)


# Getting the Full Blockchain
@web_app.route('/get_blockchain', methods=['GET'])
def get_blockchain():

    global user_logged_in
    if user_logged_in is False:
        return redirect(url_for('index'))

    # This statement will replace the blockchain with the longest blockchain everytime before display
    blockchain.replace_chain()

    chain = blockchain.chain
    length = len(chain)
    return render_template('get_blockchain.html', chain=chain, length=length, username=username)


@web_app.route('/is_valid', methods=['GET'])
def is_valid():

    global user_logged_in
    if user_logged_in is False:
        return redirect(url_for('index'))

    validity = blockchain.is_chain_valid(blockchain.chain)
    if validity is True:
        response = {'message': 'blockchain is valid'}
    else:
        response = {'message': 'blockchain is invalid'}
    return jsonify(response), 200


# Decentralizing the Blockchain
@web_app.route('/connect_node', methods=['GET', 'POST'])
def connect_node():

    global user_logged_in
    if user_logged_in is False:
        return redirect(url_for('index'))

    if request.method == 'POST':
        node_address = request.form['nodeid']
        print(node_address)
        node_address = str(node_address).strip()
        blockchain.add_node(node_address)
        print("\n\n***NODE", node_address, "SUCCESSFULLY ADDED.***\n\n")
        print("\n\n***NODES TO WHICH OUR NODE IS CONNECTED:", blockchain.nodes, '***\n\n')
        return redirect(url_for('index'))
    return render_template('connect_node.html', username=username)


# If the chain is not automatically replaced then call this URL
'''
@web_app.route('/replace_chain', methods=['GET'])
def replace_chain():
    #This URL replaces the chain at the Node if required and prints a corresponding message
    is_chain_replaced = blockchain.replace_chain()
    if is_chain_replaced:
        response = {'message': 'The Chain was Replaced by the Longest Chain in the Network',
                    'blockchain': blockchain.chain}
    else:
        response = {'message': 'This node already contains the Longest Chain',
                    'blockchain': blockchain.chain}
    return jsonify(response), 200 # Dictionaries can't be returned by the function. So they must be converted to string, tuple etc.
'''

# Running the Web App
web_app.run(host='0.0.0.0', port=5001)



















