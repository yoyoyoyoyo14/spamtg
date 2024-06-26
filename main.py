import kivy
kivy.require('2.1.0')  # Убедитесь, что версия Kivy правильная

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.clock import Clock
import asyncio
import threading
import sys
from telethon import TelegramClient, errors
from telethon.tl.functions.channels import JoinChannelRequest
import time

# Функции для работы с файлами
def load_list(filename):
    with open(filename, 'r', encoding='utf-8') as file:
        return [line.strip() for line in file.readlines()]

def load_message(filename):
    with open(filename, 'r', encoding='utf-8') as file:
        return file.read().strip()

# Функции для работы с Telegram
async def join_chat(client, chat):
    try:
        await client(JoinChannelRequest(chat))
        print(f"Joined chat {chat}")
    except Exception as e:
        print(f"Failed to join chat {chat}: {e}")

async def send_messages(api_id, api_hash, phone, chats, message):
    client = TelegramClient(phone, api_id, api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        try:
            await client.send_code_request(phone)
            code = input(f'Enter the code for {phone}: ')
            await client.sign_in(phone, code)
        except errors.SessionPasswordNeededError:
            password = input(f'Enter the password for {phone}: ')
            await client.sign_in(password=password)
    for chat in chats:
        try:
            await client.send_message(chat, message)
            print(f'Message sent to {chat}')
        except errors.ChatWriteForbiddenError:
            await join_chat(client, chat)
            try:
                await client.send_message(chat, message)
                print(f'Message sent to {chat}')
            except Exception as e:
                print(f'Failed to send message to {chat} after joining: {e}')
        except Exception as e:
            print(f'Failed to send message to {chat}: {e}')
    await client.disconnect()

# Основная функция
async def main(cooldown):
    accounts = load_list('accounts.txt')
    chats = load_list('chats.txt')
    message = load_message('message.txt')
    try:
        while True:
            tasks = []
            for account in accounts:
                api_id, api_hash, phone = account.split(':')
                tasks.append(send_messages(api_id, api_hash, phone, chats, message))
            await asyncio.gather(*tasks)
            print(f"All messages sent, waiting for {cooldown} seconds...")
            await asyncio.sleep(cooldown)
    except asyncio.CancelledError:
        print("Main task cancelled, exiting...")
        return

# Функция для запуска асинхронного кода в отдельном потоке
def start_async_loop(loop, cooldown):
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main(cooldown))

# Функция для остановки цикла событий
def stop_loop(loop):
    for task in asyncio.all_tasks(loop):
        task.cancel()
    loop.call_soon_threadsafe(loop.stop)

# Класс для консольного вывода в Kivy
class ConsoleOutput:
    def __init__(self, label):
        self.label = label
        self.buffer = ""

    def write(self, message):
        self.buffer += message
        self.label.text = self.buffer

    def flush(self):
        pass

# Основное приложение Kivy
class TelegramBotApp(App):
    def build(self):
        self.running = False
        self.async_loop = None
        self.async_thread = None
        self.cooldown = 3630

        layout = BoxLayout(orientation='vertical')
        
        self.console_output = Label(size_hint_y=None, height=300)
        sys.stdout = ConsoleOutput(self.console_output)
        sys.stderr = sys.stdout

        layout.add_widget(Button(text='Start', on_press=self.start_bot))
        layout.add_widget(Button(text='Stop', on_press=self.stop_bot))
        layout.add_widget(Button(text='Change Cooldown', on_press=self.change_cooldown))
        layout.add_widget(Button(text='Refresh', on_press=self.refresh_console))
        layout.add_widget(self.console_output)
        
        return layout

    def start_bot(self, instance):
        if not self.running:
            self.running = True
            self.async_loop = asyncio.new_event_loop()
            self.async_thread = threading.Thread(target=start_async_loop, args=(self.async_loop, self.cooldown))
            self.async_thread.start()

    def stop_bot(self, instance):
        if self.running:
            self.running = False
            stop_loop(self.async_loop)
            self.async_thread.join()

    def change_cooldown(self, instance):
        new_cooldown = TextInput(text=str(self.cooldown))
        self.cooldown = int(new_cooldown.text)
        print(f"Cooldown changed to {self.cooldown} seconds")

    def refresh_console(self, instance):
        self.console_output.text = ''

if __name__ == '__main__':
    TelegramBotApp().run()
