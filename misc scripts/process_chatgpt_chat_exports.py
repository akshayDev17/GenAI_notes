# TODO
# using a particular account, export the chat session 
# give the user a command line interactive session to choose which chat session to download
# download the chat session as a cleaned up: 1. chat.html, 2. chat.json, 3. chat.pdf

import argparse, json
from typing import Dict

class Node:
    def __init__(self, id, message, parent, children):
        self.id = id
        self.message = message
        self.parent = parent
        self.children_ids = children
        self.children = None
    
    def __str__(self):
        if self.message is not None:
            return json.dumps(
                {
                    'id': self.id,
                    'message': self.message["author"]["role"],
                    'parent': self.parent,
                    'children_ids': self.children_ids,
                },
                indent=2
            )
        return json.dumps(
            {
                'id': self.id,
                'message': "",
                'parent': self.parent,
                'children_ids': self.children_ids,
            },
            indent=2
        )
    
    def next(self):
        if isinstance(self.children, list) and len(self.children) > 0:
            return self.children[-1]

def join_nodes(node_map: Dict[str, Node]):
    for node_id in list(node_map.keys()):
        child_nodes = []
        for child_node_id in node_map[node_id].children_ids:
            child_nodes.append(node_map[child_node_id])
        node_map[node_id].children = child_nodes

def print_tree(head_node: Node, level=0, prefix="Root: "):
    print(" " * (level * 4) + prefix + str(head_node.id))
    for i, child in enumerate(head_node.children):
        print_tree(child, level + 1, f"C{i+1}--- ")

def find_user_node(curr_node: Node):
    if curr_node is None:
        return None
    while curr_node is not None:
        if curr_node.message is not None and curr_node.message['author']['role'] == 'user':
            return curr_node
        curr_node = curr_node.next()
    return curr_node

def process_raw_chats_json(json_file_path: str):
    '''
    Process raw chat session exported from chat gpt within the json file having the file path `json_file_path`
    This file could contain one or more chat sessions 
    Creates the following:
        1. a cleaned up chat.html (TODO)
        2. a cleaned up version of the raw chatgpt json file
        3. a PDF corresponding to the chat session captured within json_file_path
    Arguments:
        1. json_file_path: string argument corresponding to the downloaded raw chat.json file
    Returns:

    '''
    with open(json_file_path, 'r') as infile:
        parent_json_obj = json.load(infile)
    print(f"{len(parent_json_obj)} sessions were found.")

    for chat_session in parent_json_obj:
        name = chat_session['title']
        chat_session_json = chat_session["mapping"]

        # each json item of the chat session is an object having the following properties:
        # 1. id
        # 2. message 
        # 3. parent
        # 4. children
        # so convert each constituent json item into this object
        node_map = {}
        for node_id, node_details in  chat_session_json.items():
            node_map[node_id] = Node(**node_details)
        join_nodes(node_map)

        curr_node = node_map[list(chat_session_json.keys())[0]]
        print_tree(curr_node)

        # TODO: incorporate usage of all children
        cleaned_chat_session_json = []
        while curr_node is not None:
            user_question = None
            curr_node = find_user_node(curr_node)
            if curr_node is None:
                break

            # user is found, record the user question
            user_question = curr_node.message["content"]["parts"]
            if user_question is not None:
                # iterate through the linked list and find the relevant assistant answer
                while curr_node is not None and (
                    curr_node.message['author']['role'] != 'assistant' or (curr_node.message['author']['role'] == 'assistant' and curr_node.message["content"]["parts"] == [""])
                ):
                    curr_node = curr_node.next()
                if curr_node is not None:
                    cleaned_chat_session_json.append({
                        'user': user_question,
                        'answer': curr_node.message["content"]["parts"]
                    })
                    curr_node = find_user_node(curr_node)
        
        # write session to a json in a cleaned format
        with open(f"conversations_{name}.json", "w+") as outfile:
            json.dump(cleaned_chat_session_json, outfile, indent=2)

        with open("template.html", 'r') as infile:
            complete_code = infile.read()

        with open("chat_container_template.html", "r") as infile:
            chat_container_template = infile.read()

        with open("navigation_template.html", "r") as infile:
            navigation_template_code = infile.read()


        chat_container_html_code, chat_data = "", {}
        for i in range(len(cleaned_chat_session_json)):
            navigation_code = ""
            if len(cleaned_chat_session_json[i]['answer']) > 1:
                navigation_code = navigation_template_code.format(question_number = i+1)
            chat_container_html_code += chat_container_template.format(
                question_number = i+1, 
                user_question = "".join(cleaned_chat_session_json[i]['user']), 
                navigation_html_code = navigation_code
            )

            chat_data[f'question-{i+1}'] = [x.replace("\n\n", "\n") for x in cleaned_chat_session_json[i]['answer']]
        
        complete_code = complete_code.replace("chat_container_code", chat_container_html_code).replace("chat_data", f"{json.dumps(chat_data, indent=2)}")

        with open(f'conversations_{name}.html', 'w+') as outfile:
            outfile.write(complete_code)


def main():
    process_raw_chats_json(json_file_path='./conversations.json')

if __name__ == '__main__':
    main()