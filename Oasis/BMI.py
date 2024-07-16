import socket
import json
import threading
import tkinter as tk
from tkinter import simpledialog, scrolledtext
import argparse
import sys

# Server Code
HOST = '127.0.0.1'
PORT = 5000
ADDR = (HOST, PORT)
BUFFER_SIZE = 1024

clients = []
rooms = {}


def handle_client(client_socket):
    while True:
        try:
            message = client_socket.recv(BUFFER_SIZE).decode('utf-8')
            if message:
                handle_message(client_socket, message)
            else:
                remove_client(client_socket)
                break
        except:
            remove_client(client_socket)
            break


def handle_message(client_socket, message):
    try:
        data = json.loads(message)
        action = data['action']

        if action == 'join':
            room = data['room']
            if room not in rooms:
                rooms[room] = []
            rooms[room].append(client_socket)
            broadcast(room, f"{data['username']} joined the room.", client_socket)
        elif action == 'message':
            room = data['room']
            broadcast(room, f"{data['username']}: {data['message']}", client_socket)
    except json.JSONDecodeError:
        pass


def broadcast(room, message, client_socket):
    for client in rooms.get(room, []):
        try:
            client.send(message.encode('utf-8'))
        except:
            remove_client(client)


def remove_client(client_socket):
    for room, clients in rooms.items():
        if client_socket in clients:
            clients.remove(client_socket)
            if not clients:
                del rooms[room]
            break


def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(ADDR)
    server_socket.listen()

    print("Server started, waiting for connections...")

    while True:
        client_socket, addr = server_socket.accept()
        print(f"New connection from {addr}")
        clients.append(client_socket)
        thread = threading.Thread(target=handle_client, args=(client_socket,))
        thread.start()


# Client Code
class Client:
    def __init__(self, username):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client_socket.connect(ADDR)
        except ConnectionRefusedError:
            print("Connection to server failed. Make sure the server is running.")
            sys.exit(1)
        self.username = username

    def join_room(self, room):
        message = json.dumps({"action": "join", "room": room, "username": self.username})
        self.client_socket.send(message.encode('utf-8'))

    def send_message(self, room, message):
        data = {"action": "message", "room": room, "username": self.username, "message": message}
        self.client_socket.send(json.dumps(data).encode('utf-8'))

    def receive_messages(self):
        while True:
            try:
                message = self.client_socket.recv(BUFFER_SIZE).decode('utf-8')
                if message:
                    print(message)
            except ConnectionResetError:
                print("Connection to server lost.")
                break


# GUI Code
class ChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Chat Application")

        self.chat_area = scrolledtext.ScrolledText(root, wrap=tk.WORD)
        self.chat_area.pack(padx=20, pady=5)
        self.chat_area.config(state=tk.DISABLED)

        self.message_entry = tk.Entry(root, width=50)
        self.message_entry.pack(padx=20, pady=5)
        self.message_entry.bind("<Return>", self.send_message)

        self.username = simpledialog.askstring("Username", "Enter your username:")
        self.room = simpledialog.askstring("Room", "Enter room name:")

        if not self.username or not self.room:
            print("Username and room name are required.")
            self.root.destroy()
            return

        try:
            self.client = Client(self.username)
            self.client.join_room(self.room)
        except Exception as e:
            print(f"Failed to connect to server: {e}")
            self.root.destroy()
            return

        threading.Thread(target=self.receive_messages, daemon=True).start()

    def receive_messages(self):
        while True:
            try:
                message = self.client.client_socket.recv(BUFFER_SIZE).decode('utf-8')
                if message:
                    self.chat_area.config(state=tk.NORMAL)
                    self.chat_area.insert(tk.END, message + "\n")
                    self.chat_area.config(state=tk.DISABLED)
                    self.chat_area.see(tk.END)
            except ConnectionResetError:
                print("Connection to server lost.")
                break
            except Exception as e:
                print(f"An error occurred: {e}")
                break

    def send_message(self, event=None):
        message = self.message_entry.get()
        self.message_entry.delete(0, tk.END)
        if message.strip():
            self.client.send_message(self.room, message)


# Main Function to Run Server or Client
def main():
    parser = argparse.ArgumentParser(description="Chat Application")
    parser.add_argument("mode", choices=["server", "client"], help="Start in server or client mode")
    args = parser.parse_args()

    if args.mode == "server":
        start_server()
    elif args.mode == "client":
        root = tk.Tk()
        app = ChatApp(root)
        root.mainloop()


if __name__ == "__main__":
    main()
